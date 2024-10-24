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
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
INTERNAL_IPS = ["127.0.0.1"]

DEPLOYED_SITE_NAME = "127.0.0.1"

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
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
        'PASSWORD': 'postgres',
        'HOST': '127.0.0.1',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/
LANGUAGE_CODE = 'en'
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

SITE_ID = 1

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

DEFAULT_AUTO_FIELD='django.db.models.AutoField'

# Memcache settings
CLIENT_URL = '127.0.0.1:11211'

# Celery settings
## use True for testing and False when you use rabbitMQ and celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_TASK_ALWAYS_EAGER = False
CELERY_CACHE_BACKEND = 'memcached'
CELERY_BROKER_CONNECTION_MAX_RETRIES = 2
CELERY_RESULT_BACKEND = "cache+memcached://127.0.0.1:11211/"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = 'Africa/Nairobi'
CELERY_ROUTES = {
    'tally_ho.apps.tally.management.commands.*': {
        'queue': 'tally_data_import',
    }
}

# Quaritine trigger data
QUARANTINE_DATA = [
    {'name': 'Registrants trigger',
     'description':
     str('Summation of the number of cancelled ballots and '
         'the number of ballots inside the box must be less than or equal to '
         'the number of registered voters at the station.'),
     'method': 'pass_registrants_trigger',
     'active': True,
     'value': 0,
     'percentage': 0
     },
    {'name': 'Voter cards trigger',
     'description':
     str('Summation of the number of cancelled ballots and '
         'the number of ballots inside the box must be equal to '
         'the number of voter cards in the ballot box.'),
     'method': 'pass_voter_cards_trigger',
     'active': True,
     'value': 0,
     'percentage': 0
     },
    {'name': 'Ballot papers trigger',
     'description':
     str('The total number of ballots received by the polling station must be'
         ' equal to total number of ballots found inside and outside the '
         'ballot box.'),
     'method': 'pass_ballot_papers_trigger',
     'active': True,
     'value': 0,
     'percentage': 0
     },
    {'name': 'Ballot inside the box trigger',
     'description':
     str('The total number of ballots found inside the ballot box must be '
         'equal to the summation of the number of unstamped ballots and the '
         'number of invalid votes (including the blanks) and '
         'the number of valid votes.'),
     'method': 'pass_ballot_inside_box_trigger',
     'active': True,
     'value': 0,
     'percentage': 0
     },
    {'name': 'Candidates votes trigger',
     'description':
     str('The total number of the sorted and counted ballots must be '
         'equal to the total votes distributed among the candidates.'),
     'method': 'pass_candidates_votes_trigger',
     'active': True,
     'value': 0,
     'percentage': 0
     },
]

ELECTROL_RACES = [
    {
        'type': 'GENERAL',
        'code': 0,
        'ballot_name': 'ballot_number_general'
    },
    {
        'type': 'WOMEN',
        'code': 1,
        'ballot_name': 'ballot_number_women'
    },
    {
        'type': 'COMPONENT_AMAZIGH',
        'code': 2,
        'ballot_name': 'ballot_number_component',
        'component_ballot_numbers': ['54'],
    },
    {
        'type': 'COMPONENT_TWARAG',
        'code': 3,
        'ballot_name': 'ballot_number_component',
        'component_ballot_numbers': ['55', '57'],
    },
    {
        'type': 'COMPONENT_TEBU',
        'code': 4,
        'ballot_name': 'ballot_number_component',
        'component_ballot_numbers': ['56', '58'],
    },
    {
        'type': 'PRESIDENTIAL',
        'code': 5,
        'ballot_name': 'ballot_number_presidential',
    },
]

# Maps ballot file columns names in to Electrol race Model fields
BALLOT_COLS_TO_ELECTROL_RACE_MODEL_FIELDS_MAPPING = {
    'election_level': 'election_level',
    'sub_type': 'ballot_name'
}

BALLOT_NAME_COLUMN_NAME_IN_BALLOT_FILE = 'number'

CONSTITUENCY_COLUMN_NAME_IN_SUB_CONSTITUENCY_FILE = 'constituency_name'

SUB_CONSTITUENCY_COD_COL_NAME_IN_SUB_CON_BALLOTS_FILE = 'sub_constituency_code'

BALLOT_NUMBER_COL_NAME_IN_SUB_CON_BALLOTS_FILE = 'ballot_number'

BALLOT_COLUMN_NAMES = ['election_level', 'sub_type', 'number']

SUB_CONSTITUENCY_COLUMN_NAMES = ['sub_constituency_code',
                                 'number_of_ballots',
                                 'sub_constituency_name',
                                 'constituency_name']

# Maps sub constituency file columns names to SubConstituency Model fields
SUB_CON_FILE_COLS_NAMES_TO_SUB_CON_MODEL_FIELDS =\
{
    'sub_constituency_code' : 'code',
    'number_of_ballots': 'number_of_ballots',
    'sub_constituency_name': 'name',
    'constituency_name': 'constituency'
}

# Maps result form file columns to ResultForm Model fields
RESULT_FORM_FILE_COLS_NAMES_TO_RESULT_FORM_MODEL_FIELDS =\
{
    'station_number': 'station_number',
    'name': 'name',
    'barcode': 'barcode',
    'serial_number': 'serial_number',
    'gender': 'gender',
    'center_code': 'center',
    'office_name': 'office',
    'ballot_number' : 'ballot',
    'region_name': 'region'
}
# Maps stations file columns to Station Model fields
STATIONS_FILE_COLS_NAMES_TO_STATION_MODEL_FIELDS =\
{
    'center_code': 'center',
    'center_name': 'center_name',
    'sub_constituency_code': 'sub_constituency',
    'station_number': 'station_number',
    'station_gender': 'gender',
    'station_registrants': 'registrants',
}

SUB_CONSTITUENCY_BALLOTS_COLUMN_NAMES = ['sub_constituency_code',
                                         'ballot_number',]

CENTER_COLUMN_NAMES = ['center_id', 'name', 'center_type', 'center_lat',
                       'center_lon', 'office_name', 'office_id', 'region_name',
                       'constituency_name', 'subconstituency_id',
                       'mahalla_name', 'village_name']

# Maps centers file columns to Center Model fields
CENTERS_FILE_COLS_NAMES_TO_CENTER_MODEL_FIELDS =\
{
    'center_id': 'code',
    'name': 'name',
    'center_type': 'center_type',
    'center_lat': 'latitude',
    'center_lon': 'longitude',
    'office_name': 'office',
    'region_name': 'region',
    'constituency_name': 'constituency',
    'subconstituency_id': 'sub_constituency',
    'mahalla_name': 'mahalla',
    'village_name': 'village',
}

# Maps centers file columns to Office Model fields
CENTERS_FILE_COLS_NAMES_TO_OFFICE_MODEL_FIELDS =\
{
    'office_name': 'name',
    'office_id': 'number',
    'region_name': 'region',
}

REGION_COL_NAME_IN_CENTERS_CSV_FILE = 'region_name'

STATION_COLUMN_NAMES = ['center_code', 'center_name', 'sub_constituency_code',
                        'station_number', 'station_gender',
                        'station_registrants']

RESULT_FORM_COLUMN_NAMES = ['ballot_number', 'center_code', 'station_number',
                            'gender', 'name', 'office_name', 'barcode',
                            'serial_number', 'region_name']

CANDIDATE_COLUMN_NAMES =\
    ['candidate_id', 'candidate_full_name', 'ballot_number', 'race_type']

# Maps candidates file columns to Candidate Model fields
CANDIDATE_FILE_COLS_NAMES_TO_CANDIDATE_MODEL_FIELDS =\
{
    'candidate_full_name': 'full_name',
    'candidate_id': 'candidate_id',
    'ballot_number': 'ballot',
    'race_type': 'electrol_race',
}

BALLOT_ORDER_COLUMN_NAMES = ['candidate_id', 'ballot_order']

CANDIDATE_RESULTS_PPT_COVER_PAGE_BCK_IMG_PATH =\
    'tally_ho/apps/tally/static/images/HNEC.jpg'

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
