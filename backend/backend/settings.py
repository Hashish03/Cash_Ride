from pathlib import Path
import os  # Add this import for environment variables

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-gwp$ej3y)@nj!we4k@(!z-e$ukmlyh(pu)9vu=yg+40lgwioy1'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Your apps
    'backend',
    'users',
    'drivers',
    'rides',
    'payments',
    'authentication',
    
    
    # Add any other apps from your project that have models.py
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'backend.backend.middleware.SupabaseAuthMiddleware',
]

AUTH_USER_MODEL = 'users.User'

# Add these Supabase settings before the SOCIAL_AUTH_PROVIDERS
SUPABASE_GOOGLE_CLIENT_ID = os.environ.get('SUPABASE_GOOGLE_CLIENT_ID', '')
SUPABASE_GOOGLE_CLIENT_SECRET = os.environ.get('SUPABASE_GOOGLE_CLIENT_SECRET', '')
SUPABASE_FACEBOOK_APP_ID = os.environ.get('SUPABASE_FACEBOOK_APP_ID', '')
SUPABASE_FACEBOOK_APP_SECRET = os.environ.get('SUPABASE_FACEBOOK_APP_SECRET', '')

# Configure allowed social auth providers
SOCIAL_AUTH_PROVIDERS = {
    'google': {
        'client_id': SUPABASE_GOOGLE_CLIENT_ID,  # Reference the variable directly
        'client_secret': SUPABASE_GOOGLE_CLIENT_SECRET,
    },
    'facebook': {
        'client_id': SUPABASE_FACEBOOK_APP_ID,
        'client_secret': SUPABASE_FACEBOOK_APP_SECRET,
    },
    # Add other providers as needed
}

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'cash_ride_db'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'