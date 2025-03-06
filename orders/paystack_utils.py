# orders/paystack_utils.py

import requests
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

def verify_paystack_payment(transaction_id):
    url = f'https://api.paystack.co/transaction/verify/{transaction_id}'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'
    }
    response = requests.get(url, headers=headers)
    logger.info(f"Paystack verification response status code: {response.status_code}")
    logger.info(f"Paystack verification full response: {response.json()}")
    if response.status_code == 200:
        return response.json()
    logger.error(f"Paystack verification failed with status code: {response.status_code}")
    return None
