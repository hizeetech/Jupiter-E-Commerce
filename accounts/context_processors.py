# accounts/context_processors.py
from vendor.models import Vendor
from django.conf import settings
from accounts.models import UserProfile

def get_vendor(request):
    try:
        vendor = Vendor.objects.get(user=request.user)
    except:
        vendor = None
    return dict(vendor=vendor)

def get_user_profile(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except:
        user_profile = None
    return dict(user_profile=user_profile)


def get_google_api(request):
    return {'GOOGLE_API_KEY': settings.GOOGLE_API_KEY}


def get_paypal_client_id(request):
    return {'PAYPAL_CLIENT_ID': settings.PAYPAL_CLIENT_ID}

def get_paystack_secret_key(request):
    return {'PAYSTACK_SECRET_KEY': settings.PAYSTACK_SECRET_KEY}


def get_paystack_public_key(request):
    return {'PAYSTACK_PUBLIC_KEY': settings.PAYSTACK_PUBLIC_KEY}


def get_flutterwave_public_key(request):
    return {'FLUTTERWAVE_PUBLIC_KEY': settings.FLUTTERWAVE_PUBLIC_KEY}


def get_flutterwave_secret_key(request):
    return {'FLUTTERWAVE_SECRET_KEY': settings.FLUTTERWAVE_SECRET_KEY}