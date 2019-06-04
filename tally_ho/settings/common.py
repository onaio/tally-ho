"""
Django settings for libya tally project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'el7%8*2=m()uxvg%ebet#o81y(qi%yi-k&&4iz^z=sces+i9lt'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
ALLOWED_HOSTS = ['localhost']
INTERNAL_IPS = ["127.0.0.1"]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_nose',
    'guardian',
    'reversion',
    'tally_ho.apps.tally',
    'tracking',
)

MIDDLEWARE = (
    'tracking.middleware.VisitorTrackingMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'tally_ho.libs.middleware.idle_timeout.IdleTimeout',
    'tally_ho.libs.middleware.user_restrict.UserRestrictMiddleware',
    'tally_ho.libs.middleware.disable_clientside_caching.'
    'DisableClientsideCachingMiddleware',
    'tally_ho.libs.middleware.exception_logging.ExceptionLoggingMiddleware',
)

ROOT_URLCONF = 'tally_ho.urls'

WSGI_APPLICATION = 'tally_ho.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'tally',
        'USER': 'postgres',
        'PASSWORD': 'tally',
        'HOST': '127.0.0.1',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# media base
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'guardian.backends.ObjectPermissionBackend',
)

ANONYMOUS_USER_ID = -1

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'libs', 'templates'),
                 os.path.join(BASE_DIR, 'apps', 'tally', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'tally_ho.libs.utils.context_processors.debug',
                'tally_ho.libs.utils.context_processors.is_superadmin',
                'tally_ho.libs.utils.context_processors.is_tallymanager',
                'tally_ho.libs.utils.context_processors.locale',
                'tally_ho.libs.utils.context_processors.site_name',
            ],
            # SECURITY WARNING: don't run with debug turned on in production!
            'debug': True
        },
    },
]

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

SITE_ID = 1

NOSE_ARGS = [
    '--with-coverage',
    '--cover-package=tally_ho'
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

LOGIN_REDIRECT_URL = '/'

# CONSTANTS
MIN_STATION_VALUE = 1
MAX_STATION_VALUE = 102

# Limit uploads to 10MB
MAX_FILE_UPLOAD_SIZE = 10485760

# Switch to True on production
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# In minutes
IDLE_TIMEOUT = 60

# Individual pageviews will be tracked
TRACK_PAGEVIEWS = True

LOCALE_PATHS = (os.path.realpath(os.path.join(BASE_DIR, '..', 'locale')),)

# Logging
LOG_FILE_PATH = os.path.join(BASE_DIR, '..', 'dev.log')

# Logout Redirect
LOGOUT_REDIRECT_URL = "/"
