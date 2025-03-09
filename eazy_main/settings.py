# eazy_main/settings.py
"""
Django settings for eazy_main project.

Generated by 'django-admin startproject' using Django 5.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
from decouple import config
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = ['172.234.201.226', '127.0.0.1', 'mart9ja.com', 'www.mart9ja.com']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'accounts',
    'vendor',
    'store',
    'marketplace',
    'django.contrib.gis',
    'customers',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'orders.request_object.RequestObjectMiddleware', # custom middleware created to access the request object in models.py
]

ROOT_URLCONF = 'eazy_main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.get_vendor',
                'accounts.context_processors.get_google_api',
                'marketplace.context_processors.get_cart_counter',
                'marketplace.context_processors.get_cart_amounts',
                'accounts.context_processors.get_user_profile',
                'accounts.context_processors.get_paypal_client_id',
                'accounts.context_processors.get_paystack_secret_key',
                'accounts.context_processors.get_paystack_public_key',
                'accounts.context_processors.get_flutterwave_public_key',
                'accounts.context_processors.get_flutterwave_secret_key',
                'accounts.context_processors.get_monnify_secret_key',
                'accounts.context_processors.get_monnify_api_key',
                'accounts.context_processors.get_monnify_contract_code',
                
            ],
        },
    },
]

WSGI_APPLICATION = 'eazy_main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.postgresql',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
    }
}


AUTH_USER_MODEL = 'accounts.User'


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'GMT'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR /'static'
STATICFILES_DIRS = [
    'eazy_main/static'
]

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR /'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

# Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Email configuration settings
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_SSL = True

DEFAULT_FROM_EMAIL = 'Mart9ja Support <support@mart9ja.com>'

GOOGLE_API_KEY = config('GOOGLE_API_KEY')

os.environ['PATH'] = os.path.join(BASE_DIR, 'env\Lib\site-packages\osgeo') + ';' + os.environ['PATH']
os.environ['PROJ_LIB'] = os.path.join(BASE_DIR, 'env\Lib\site-packages\osgeo\data\proj') + ';' + os.environ['PATH']
GDAL_LIBRARY_PATH = os.path.join(BASE_DIR, 'env\Lib\site-packages\osgeo\gdal.dll')

PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID')

SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

#PAYSTACK_SECRET_KEY = 'sk_test_a27e0fb00844f9ebc243354bf8ae1e03d8e56619'
#PAYSTACK_PUBLIC_KEY = 'pk_test_bf0820e2d1070f515fe2ef79b29a38122a8166ed'

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY')

FLUTTERWAVE_PUBLIC_KEY = config('FLUTTERWAVE_PUBLIC_KEY')
FLUTTERWAVE_SECRET_KEY = config('FLUTTERWAVE_SECRET_KEY')

MONNIFY_API_KEY = config('MONNIFY_API_KEY')
MONNIFY_SECRET_KEY = config('MONNIFY_SECRET_KEY')
MONNIFY_CONTRACT_CODE = config('MONNIFY_CONTRACT_CODE')


