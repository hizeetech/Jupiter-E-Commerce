# orders/views.py
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from store.models import ProductItem
from .utils import generate_order_number, order_total_by_vendor
from marketplace.models import Cart, Tax
from marketplace.context_processors import get_cart_amounts
from .forms import OrderForm
from .models import Order, OrderedProduct, Payment
import simplejson as json
from accounts.utils import send_notification
from django.contrib.sites.shortcuts import get_current_site


from django.conf import settings
from .paystack_utils import verify_paystack_payment
from django.views.decorators.csrf import csrf_exempt

import logging
logger = logging.getLogger(__name__)



@login_required(login_url='login')
def place_order(request):
  cart_items = Cart.objects.filter(user=request.user).order_by('created_at')
  cart_count = cart_items.count()
  if cart_count <= 0:
      return redirect('marketplace')

  vendors_ids = []
  for i in cart_items:
      if i.productitem.vendor.id not in vendors_ids:
          vendors_ids.append(i.productitem.vendor.id)
  
  # {"vendor_id":{"subtotal":{"tax_type": {"tax_percentage": "tax_amount"}}}}
  get_tax = Tax.objects.filter(is_active=True)
  subtotal = 0
  total_data = {}
  k = {}
  for i in cart_items:
      productitem = ProductItem.objects.get(pk=i.productitem.id, vendor_id__in=vendors_ids)
      v_id = productitem.vendor.id
      if v_id in k:
          subtotal = k[v_id]
          subtotal += (productitem.price * i.quantity)
          k[v_id] = subtotal
      else:
          subtotal = (productitem.price * i.quantity)
          k[v_id] = subtotal
  
      # Calculate the tax_data
      tax_dict = {}
      for i in get_tax:
          tax_type = i.tax_type
          tax_percentage = i.tax_percentage
          tax_amount = round((tax_percentage * subtotal)/100, 2)
          tax_dict.update({tax_type: {str(tax_percentage) : str(tax_amount)}})
      # Construct total data
      total_data.update({productitem.vendor.id: {str(subtotal): str(tax_dict)}})
    
  subtotal = get_cart_amounts(request)['subtotal']
  total_tax = get_cart_amounts(request)['tax']
  grand_total = get_cart_amounts(request)['grand_total']
  tax_data = get_cart_amounts(request)['tax_dict']
  
  if request.method == 'POST':
    form = OrderForm(request.POST)
    if form.is_valid():
      order = Order()
      order.first_name = form.cleaned_data['first_name']
      order.last_name = form.cleaned_data['last_name']
      order.phone = form.cleaned_data['phone']
      order.email = form.cleaned_data['email']
      order.address = form.cleaned_data['address']
      order.country = form.cleaned_data['country']
      order.state = form.cleaned_data['state']
      order.city = form.cleaned_data['city']
      order.zip_code = form.cleaned_data['zip_code']
      order.user = request.user
      order.total = grand_total
      order.tax_data = json.dumps(tax_data)
      order.total_data = json.dumps(total_data)
      order.total_tax = total_tax
      order.payment_method = request.POST['payment_method']
      order.save() # order id/ pk is generated
      order.order_number = generate_order_number(order.id)
      order.vendors.add(*vendors_ids)
      order.save()
      context = {
        'order': order,
        'cart_items': cart_items,
        'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
        'FLUTTERWAVE_PUBLIC_KEY': settings.FLUTTERWAVE_PUBLIC_KEY
      }
      return render(request, 'orders/place_order.html', context)
    else:
      print(form.errors)
  
  return render(request, 'orders/place_order.html')


@login_required(login_url='login')
def payments(request):
	# Check if the request is ajax or not
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
	# STORE THE PAYMENT DETAILS IN THE PAYMENT MODEL
        order_number = request.POST.get('order_number')
        transaction_id = request.POST.get('transaction_id')
        payment_method = request.POST.get('payment_method')
        status = request.POST.get('status')

        order = Order.objects.get(user=request.user, order_number=order_number)
        payment = Payment(
            user = request.user,
            transaction_id = transaction_id,
            payment_method = payment_method,
            amount = order.total,
            status = status
        )
        payment.save()

        # Verify Paystack payment if applicable
        if payment_method == 'Paystack':
            transaction_data = verify_paystack_payment(transaction_id)
            logger.info(f"Paystack verification response: {transaction_data}")
            if not transaction_data or transaction_data.get('status') != 'success':
                logger.error(f"Paystack verification failed for transaction {transaction_id}")
                return JsonResponse({
                    'status': 'fail',
                    'message': 'Payment verification failed'
                }, status=400)
            
            # Update status from Paystack response
            status = transaction_data.get('gateway_response', 'Pending')
            
        elif payment_method == 'Flutterwave':
            from .utils import verify_flutterwave_payment
            verification = verify_flutterwave_payment(transaction_id)
            
            if not verification or verification.get('status') != 'successful':
                return JsonResponse({
                    'status': 'fail', 
                    'message': 'Flutterwave payment verification failed'
                }, status=400)
            
            verified_amount = float(verification.get('amount', 0))
            status = verification.get('status', 'Pending')
        else:
            return JsonResponse({
                'status': 'fail',
                'message': 'Unsupported payment method'
            }, status=400)

        # Validate amount matches order total
        if abs(verified_amount - float(order.total)) > 0.01:
            return JsonResponse({
                'status': 'fail',
                'message': f'Amount mismatch. Expected {order.total}, got {verified_amount}'
            }, status=400)


		# UPDATE THE ORDER MODEL
        order.payment = payment
        order.is_ordered = True
        order.save()

        # MOVE THE CART ITEMS TO ORDERED PRODUCT MODEL
        cart_items = Cart.objects.filter(user=request.user)
        for item in cart_items:
            ordered_product = OrderedProduct()
            ordered_product.order = order
            ordered_product.payment = payment
            ordered_product.user = request.user
            ordered_product.productitem = item.productitem
            ordered_product.quantity = item.quantity
            ordered_product.price = item.productitem.price
            ordered_product.amount = item.productitem.price * item.quantity # total amount
            ordered_product.save()

		# SEND ORDER CONFIRMATION EMAIL TO THE CUSTOMER
        mail_subject = 'Thank you for ordering with us.'
        mail_template = 'orders/order_confirmation_email.html'

        ordered_product = OrderedProduct.objects.filter(order=order)
        customer_subtotal = 0
        for item in ordered_product:
            customer_subtotal += (item.price * item.quantity)
        tax_data = json.loads(order.tax_data)
        context = {
            'user': request.user,
            'order': order,
            'to_email': order.email,
            'ordered_product': ordered_product,
            'domain': get_current_site(request),
            'customer_subtotal': customer_subtotal,
            'tax_data': tax_data,
        }
        send_notification(mail_subject, mail_template, context)
        

        # SEND ORDER RECEIVED EMAIL TO THE VENDOR
        mail_subject = 'You have received a new order.'
        mail_template = 'orders/new_order_received.html'
        to_emails = []
        for i in cart_items:
            if i.productitem.vendor.user.email not in to_emails:
                to_emails.append(i.productitem.vendor.user.email)

                ordered_product_to_vendor = OrderedProduct.objects.filter(order=order, productitem__vendor=i.productitem.vendor)
                print(ordered_product_to_vendor)

        
                context = {
                    'order': order,
                    'to_email': i.productitem.vendor.user.email,
                    'ordered_product_to_vendor': ordered_product_to_vendor,
                    'vendor_subtotal': order_total_by_vendor(order, i.productitem.vendor.id)['subtotal'],
                    'tax_data': order_total_by_vendor(order, i.productitem.vendor.id)['tax_dict'],
                    'vendor_grand_total': order_total_by_vendor(order, i.productitem.vendor.id)['grand_total'],
                }
                send_notification(mail_subject, mail_template, context)

        # CLEAR THE CART IF THE PAYMENT IS SUCCESS
        # cart_items.delete() 

        # RETURN BACK TO AJAX WITH THE STATUS SUCCESS OR FAILURE
        response = {
            'order_number': order_number,
            'transaction_id': transaction_id,
        }
        return JsonResponse(response)
    return HttpResponse('Payments view')


def order_complete(request):
    order_number = request.GET.get('order_no')
    transaction_id = request.GET.get('trans_id')

    try:
        order = Order.objects.get(order_number=order_number, payment__transaction_id=transaction_id, is_ordered=True)
        ordered_product = OrderedProduct.objects.filter(order=order)

        subtotal = 0
        for item in ordered_product:
            subtotal += (item.price * item.quantity)

        tax_data = json.loads(order.tax_data)
        print(tax_data)
        context = {
            'order': order,
            'ordered_product': ordered_product,
            'subtotal': subtotal,
            'tax_data': tax_data,
        }
        return render(request, 'orders/order_complete.html', context)
    except:
        return redirect('home')
    

@csrf_exempt
def paystack_webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body)
        if payload['event'] == 'charge.success':
            reference = payload['data']['reference']
            # Update your payment status here
            try:
                payment = Payment.objects.get(transaction_id=reference)
                payment.status = 'Success'
                payment.save()
            except Payment.DoesNotExist:
                pass
    return HttpResponse(status=200)