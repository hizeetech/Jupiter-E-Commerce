# orders/views.py
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
import requests

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
def place_order(request):  # sourcery skip: dict-assign-update-to-union, hoist-similar-statement-from-if, hoist-statement-from-if, inline-variable, move-assign-in-block, simplify-dictionary-update
    cart_items = Cart.objects.filter(user=request.user).order_by('created_at')
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('marketplace')

    vendors_ids = []
    for i in cart_items:
        if i.productitem.vendor.id not in vendors_ids:
            vendors_ids.append(i.productitem.vendor.id)

    # Calculate subtotal, tax, and grand total
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
            tax_amount = round((tax_percentage * subtotal) / 100, 2)
            tax_dict.update({tax_type: {str(tax_percentage): str(tax_amount)}})
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
            order.save()  # order id/ pk is generated
            order.order_number = generate_order_number(order.id)
            order.vendors.add(*vendors_ids)
            order.save()

            # Prepare context for rendering the template
            context = {
                'order': order,
                'cart_items': cart_items,
                'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY,
                'FLUTTERWAVE_PUBLIC_KEY': settings.FLUTTERWAVE_PUBLIC_KEY,
                'MONNIFY_API_KEY': settings.MONNIFY_API_KEY,
                'MONNIFY_CONTRACT_CODE': settings.MONNIFY_CONTRACT_CODE,
                'grand_total': grand_total,
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
        try:
            # Extract payment parameters with safety checks
            order_number = request.POST.get('order_number')
            transaction_id = request.POST.get('transaction_id')
            payment_method = request.POST.get('payment_method', 'Paystack')
            status = request.POST.get('status', 'Pending')

            if not all([order_number, transaction_id]):
                return JsonResponse({'status': 'fail', 'message': 'Missing required parameters'}, status=400)

            # Retrieve order with validation
            try:
                order = Order.objects.get(user=request.user, order_number=order_number)
            except Order.DoesNotExist:
                return JsonResponse({'status': 'fail', 'message': 'Order not found'}, status=404)

            # Verify Paystack payment if applicable
            if payment_method == 'Paystack':
                from .paystack_utils import verify_paystack_payment  # Lazy import
                transaction_data = verify_paystack_payment(transaction_id)
                
                if not transaction_data or transaction_data.get('status') != 'success':
                    return JsonResponse({
                        'status': 'fail',
                        'message': 'Payment verification failed'
                    }, status=400)
                
                # Update status from Paystack response
                status = transaction_data.get('gateway_response', 'Pending')

            # Create payment record
            payment = Payment.objects.create(
                user=request.user,
                transaction_id=transaction_id,
                payment_method=payment_method,
                amount=order.total,
                status=status
            )

            # Update order status
            order.payment = payment
            order.is_ordered = True
            order.save()

            # Process cart items
            cart_items = Cart.objects.filter(user=request.user)
            ordered_products = []
            for item in cart_items:
                ordered_product = OrderedProduct(
                    order=order,
                    payment=payment,
                    user=request.user,
                    productitem=item.productitem,
                    quantity=item.quantity,
                    price=item.productitem.price,
                    amount=item.productitem.price * item.quantity
                )
                ordered_products.append(ordered_product)
            
            # Bulk create for efficiency
            OrderedProduct.objects.bulk_create(ordered_products)

            # Email context preparation
            email_context = {
                'user': request.user,
                'order': order,
                'domain': get_current_site(request),
                'customer_subtotal': sum(item.amount for item in ordered_products),
                'tax_data': json.loads(order.tax_data),
                'ordered_product': ordered_products,
            }

            # Send customer confirmation
            send_notification(
                'Thank you for ordering with us.',
                'orders/order_confirmation_email.html',
                {**email_context, 'to_email': order.email}
            )

            # Send vendor notifications
            vendors_emailed = set()
            for item in cart_items:
                vendor = item.productitem.vendor.user
                if vendor.email not in vendors_emailed:
                    vendor_products = [op for op in ordered_products 
                                      if op.productitem.vendor == item.productitem.vendor]
                    
                    send_notification(
                        'You have received a new order.',
                        'orders/new_order_received.html',
                        {
                            **email_context,
                            'to_email': vendor.email,
                            'ordered_product_to_vendor': vendor_products,
                            'vendor_subtotal': sum(op.amount for op in vendor_products),
                        }
                    )
                    vendors_emailed.add(vendor.email)

            # Clear cart after successful processing
            cart_items.delete()

            return JsonResponse({
                'status': 'success',
                'order_number': order_number,
                'transaction_id': transaction_id
            })

        except Exception as e:
            # Log the error here (consider using logging module)
            print(f"Payment processing error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred during payment processing'
            }, status=500)

    return HttpResponse('Invalid request method', status=405)

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
    


