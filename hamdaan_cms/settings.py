"""
Django settings for hamdaan_cms project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR / '.env.example', override=False)

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-rijopl0_1&*&1604k^e!y*_8sr#*--q#$y4q7k=!-q)(9j2$zn')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',') if h.strip()]

SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8123').rstrip('/')

# Needed once DEBUG=False and the site is served over HTTPS behind nginx —
# Django's CSRF check compares the Origin header against this list for any
# POST arriving over a scheme other than plain same-origin HTTP.
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

if not DEBUG:
    # Reverse proxy (nginx) terminates the client connection; this tells
    # Django's request.is_secure() to trust nginx's X-Forwarded-Proto header
    # instead of assuming plain HTTP, so redirects/cookies behave correctly.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'django_ckeditor_5',

    'website',
    'admissions',
    'accounts',
    'payments',
    'students',
    'admin_console',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hamdaan_cms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.site_globals',
                'admin_console.context_processors.console_role',
            ],
        },
    },
]

WSGI_APPLICATION = 'hamdaan_cms.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True


# ---------- Static & Media ----------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------- CKEditor 5 (rich text content management) ----------
CKEDITOR_5_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
CKEDITOR_5_UPLOAD_PATH = 'ckeditor_uploads/'
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['bold', 'italic', 'underline', '|', 'bulletedList', 'numberedList', 'blockQuote', '|',
                    'link', 'imageUpload', '|', 'undo', 'redo'],
    },
}

# ---------- Auth redirects ----------
LOGIN_URL = 'accounts:login'

# ---------- Email (Gmail SMTP) ----------
# Port 465 (implicit SSL) rather than glittering's 587 (STARTTLS) — this
# network blocks outbound 587 but allows 465 (confirmed with
# Test-NetConnection: 587 TcpTestSucceeded=False, 465=True). Blank creds
# just fail-log (see hamdaan_cms/emails.py) instead of erroring.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# ---------- ZainPay ----------
ZAINPAY_PUBLIC_KEY = os.getenv('ZAINPAY_PUBLIC_KEY', '')
ZAINPAY_ZAINBOX_CODE = os.getenv('ZAINPAY_ZAINBOX_CODE', '')
ZAINPAY_BASE_URL = os.getenv('ZAINPAY_BASE_URL', 'https://sandbox.zainpay.ng')
ZAINPAY_CALLBACK_URL = os.getenv('ZAINPAY_CALLBACK_URL', '')
ZAINPAY_SECRET_KEY = os.getenv('ZAINPAY_SECRET_KEY', '')
ZAINPAY_RECONCILE_LOOKBACK_HOURS = int(os.getenv('ZAINPAY_RECONCILE_LOOKBACK_HOURS', '720'))
