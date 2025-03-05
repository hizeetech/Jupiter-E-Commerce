# orders/paystack_utils.py

import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def verify_paystack_payment(reference):
    secret_key = settings.PAYSTACK_SECRET_KEY
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    headers = {'Authorization': f'Bearer {secret_key}'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()

        if response_data['status']:  # Paystack's status field
            return {'success': True, 'data': response_data['data']}
        else:
            logger.error(f"Paystack verification failed: {response_data}")
            return {'success': False, 'error': response_data.get('message', 'Verification failed')}

    except requests.exceptions.RequestException as e:
        logger.error(f"Error verifying Paystack payment: {e}")
        return {'success': False, 'error': str(e)}
    except (KeyError, ValueError) as e: # Catch json errors, and key errors.
        logger.error(f"Error parsing Paystack response: {e}")
        return {'success': False, 'error': "Invalid Paystack response"}
