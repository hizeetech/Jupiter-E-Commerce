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
        'FLUTTERWAVE_PUBLIC_KEY': settings.FLUTTERWAVE_PUBLIC_KEY,
        'MONNIFY_API_KEY': settings.MONNIFY_API_KEY,
        'MONNIFY_CONTRACT_CODE': settings.MONNIFY_CONTRACT_CODE,
      }
      return render(request, 'orders/place_order.html', context)
    else:
      print(form.errors)
  
  return render(request, 'orders/place_order.html')



import logging
logger = logging.getLogger(__name__)


@login_required(login_url='login')
def payments(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        order_number = request.POST.get('order_number')
        transaction_id = request.POST.get('transaction_id')
        payment_method = request.POST.get('payment_method')
        status = request.POST.get('status')
        logger.info(f"order_number: {order_number}, transaction_id: {transaction_id}, payment_method: {payment_method}, status: {status}")

        if not all([order_number, transaction_id, payment_method, status]):
            return JsonResponse({
                'status': 'fail',
                'message': 'Missing required data.'
            }, status=400)

        try:
            order = Order.objects.get(user=request.user, order_number=order_number)
            payment = Payment(
                user=request.user,
                transaction_id=transaction_id,
                payment_method=payment_method,
                amount=order.total,
                status=status
            )
            payment.save()

            if payment_method == 'Paystack':
                transaction_data = verify_paystack_payment(transaction_id)
                logger.info(f"Paystack verification response: {transaction_data}")
                if not transaction_data or transaction_data.get('status') != 'success':
                    logger.error(f"Paystack verification failed for transaction {transaction_id}")
                    return JsonResponse({
                        'status': 'fail',
                        'message': 'Payment verification failed. Please contact support.'
                    }, status=400)
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

            if abs(verified_amount - float(order.total)) > 0.01:
                return JsonResponse({
                    'status': 'fail',
                    'message': f'Amount mismatch. Expected {order.total}, got {verified_amount}'
                }, status=400)

            order.payment = payment
            order.is_ordered = True
            order.save()

            # Move cart items to OrderedProduct model
            cart_items = Cart.objects.filter(user=request.user)
            for item in cart_items:
                ordered_product = OrderedProduct()
                ordered_product.order = order
                ordered_product.payment = payment
                ordered_product.user = request.user
                ordered_product.productitem = item.productitem
                ordered_product.quantity = item.quantity
                ordered_product.price = item.productitem.price
                ordered_product.amount = item.productitem.price * item.quantity
                ordered_product.save()

            # Send order confirmation email
            mail_subject = 'Thank you for ordering with us.'
            mail_template = 'orders/order_confirmation_email.html'
            ordered_products = OrderedProduct.objects.filter(order=order)
            customer_subtotal = sum(item.price * item.quantity for item in ordered_products)
            tax_data = json.loads(order.tax_data)
            context = {
                'user': request.user,
                'order': order,
                'to_email': order.email,
                'ordered_products': ordered_products,
                'domain': get_current_site(request),
                'customer_subtotal': customer_subtotal,
                'tax_data': tax_data,
            }
            send_notification(mail_subject, mail_template, context)

            # Send order received email to vendors
            mail_subject = 'You have received a new order.'
            mail_template = 'orders/new_order_received.html'
            to_emails = list(set(item.productitem.vendor.user.email for item in cart_items))
            for email in to_emails:
                vendor_products = OrderedProduct.objects.filter(order=order, productitem__vendor__user__email=email)
                context = {
                    'order': order,
                    'to_email': email,
                    'ordered_products': vendor_products,
                    'vendor_subtotal': order_total_by_vendor(order, vendor_products.first().productitem.vendor.id)['subtotal'],
                    'tax_data': order_total_by_vendor(order, vendor_products.first().productitem.vendor.id)['tax_dict'],
                    'vendor_grand_total': order_total_by_vendor(order, vendor_products.first().productitem.vendor.id)['grand_total'],
                }
                send_notification(mail_subject, mail_template, context)

            # Clear the cart
            cart_items.delete()

            # Return success response
            response = {
                'status': 'success',
                'order_number': order_number,
                'transaction_id': transaction_id,
            }
            return JsonResponse(response)

        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return JsonResponse({
                'status': 'fail',
                'message': str(e)
            }, status=400) # send 400 error with message.

    return JsonResponse({'status': 'fail', 'message': 'Invalid request'}, status=400)

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
    

