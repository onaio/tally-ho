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
    '--logging-level=INFO',
    '--cover-erase',
    '--cover-html'
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
DEFAULT_IDLE_TIMEOUT = 60

# Individual pageviews will be tracked
TRACK_PAGEVIEWS = True

LOCALE_PATHS = (os.path.realpath(os.path.join(BASE_DIR, '..', 'locale')),)

# Logging
LOG_FILE_PATH = os.path.join(BASE_DIR, '..', 'dev.log')

# Logout Redirect
LOGOUT_REDIRECT_URL = "/"

# Session variables to be persisted after a session expires
SESSION_VARS = [
    'result_form',
    'encoded_result_form_intake_start_time',
    'encoded_result_form_clearance_start_time',
    'encoded_result_form_data_entry_start_time',
    'encoded_result_form_corrections_start_time',
    'encoded_result_form_audit_start_time',
    'encoded_result_form_qa_control_start_time',
]

# Quaritine trigger data
QUARANTINE_DATA = [
    {'name': 'Trigger 1 - Guard against overvoting',
     'method': 'pass_overvote',
     'active': True,
     'value': 10,
     'percentage': 90},
    {'name': 'Trigger 2 - Guard against errors and tampering with the form',
     'method': 'pass_tampering',
     'active': True,
     'value': 3,
     'percentage': 3},
    {'name': 'Trigger 3 - Validate total number of ballots used',
     'method': 'pass_ballots_number_validation',
     'active': False,
     'value': 2,
     'percentage': 2},
    {'name': 'Trigger 4 - Validate number of signatures on the voter list',
     'method': 'pass_signatures_validation',
     'active': False,
     'value': 2,
     'percentage': 2},
    {'name': 'Trigger 5 - Validate the total number of ballots inside the box',
     'method': 'pass_ballots_inside_box_validation',
     'active': False,
     'value': 2,
     'percentage': 2},
    {'name': 'Trigger 6 - Validate sum of votes distributed to all candidates',
     'method': 'pass_sum_of_candidates_votes_validation',
     'active': False,
     'value': 2,
     'percentage': 2},
    {'name': 'Trigger 7 - Validate percentage of invalid ballots',
     'method': 'pass_invalid_ballots_percentage_validation',
     'active': False,
     'value': 80,
     'percentage': 20},
    {'name': 'Trigger 8 - Validate turnout percentage',
     'method': 'pass_turnout_percentage_validation',
     'active': False,
     'value': 100,
     'percentage': 100},
    {'name':
     'Trigger 9 - Validate percentage of votes per candidate of total votes',
     'method': 'pass_percentage_of_votes_per_candidate_validation',
     'active': False,
     'value': 50,
     'percentage': 50},
    {'name':
     'Trigger 10 - Validate percentage of blank ballots',
     'method': 'pass_percentage_of_blank_ballots_trigger',
     'active': False,
     'value': 80,
     'percentage': 20},
]
