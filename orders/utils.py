# orders/utils.py
import datetime
import simplejson as json

def generate_order_number(pk):
  # sourcery skip: inline-immediately-returned-variable
  current_datetime = datetime.datetime.now().strftime('%Y%m%d%H%M%S') #20220616233810 + pk
  order_number = current_datetime + str(pk)
  return order_number


def order_total_by_vendor(order, vendor_id):
  # sourcery skip: dict-assign-update-to-union, inline-immediately-returned-variable, inline-immediately-returned-variable
    total_data = json.loads(order.total_data)
    data = total_data.get(str(vendor_id))
    subtotal = 0
    tax = 0
    tax_dict = {}

    for key, val in data.items():
        subtotal += float(key)
        val = val.replace("'", '"')
        val = json.loads(val)
        tax_dict.update(val)

        # calculate tax
        # {'VAT': {'9.00': '6.03'}, 'WHT': {'0.00': '0.00'}}
        for i in val:
            for j in val[i]:
                tax += float(val[i][j])
    grand_total = float(subtotal) + float(tax)
    context = {
        'subtotal': subtotal,
        'tax_dict': tax_dict, 
        'grand_total': grand_total,
    }

    return context

import requests
from django.conf import settings

def verify_flutterwave_payment(transaction_id):
    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        print(f"Flutterwave verification error: {str(e)}")
        return None