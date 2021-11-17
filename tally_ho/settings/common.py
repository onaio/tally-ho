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
        'USER': 'tally',
        'PASSWORD': 'tally',
        'HOST': '127.0.0.1',
    }
}

# Celery settings
## use True for testing and False when you use rabbitMQ and celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_TASK_ALWAYS_EAGER = False
CELERY_CACHE_BACKEND = 'memory'
CELERY_BROKER_CONNECTION_MAX_RETRIES = 2
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = 'Africa/Nairobi'
CELERY_ROUTES = {
    'tally_ho.libs.views.exports.export_candidate_votes': {
        'queue': 'export_candidate_votes'}
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

# NOSE_ARGS = [
#     '--logging-level=INFO',
#     '--cover-erase',
#     '--cover-html'
# ]

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
     'description':
     str('Check to guard against overvoting. '
         'If the result form does not have a reconciliation form this trigger '
         ' will always pass. '
         'If the station for this result_form has an empty registrants field '
         'this trigger will always pass. '
         'Fails if the number of ballots reported to be used in a '
         'station exceeds the number of potential voters minus the number '
         'of registrants plus N persons to accomodate staff and security.'),
     'method': 'pass_overvote',
     'active': True,
     'value': 10,
     'percentage': 90},
    {'name': 'Trigger 2 - Guard against errors and tampering with the form',
     'description':
     str('Guard against errors and tampering with the form. '
         'If the result form does not have a reconciliation form this trigger '
         'will always pass. '
         'Fails if the sum of the results section of the form does not equal '
         'the number of ballots expected based on the calculation of the '
         'key fields from the reconciliation form with a N% tolerance.'),
     'method': 'pass_tampering',
     'active': True,
     'value': 3,
     'percentage': 0},
    {'name': 'Trigger 3 - Validate total number of ballots used',
     'description':
     str('Validate that the total number of received ballots equals the '
         'total of the ballots inside the box plus ballots outside the box.'
         ' If the result form does not have a reconciliation form this trigger'
         ' will always pass.'),
     'method': 'pass_ballots_number_validation',
     'active': False,
     'value': 2,
     'percentage': 0},
    {'name': 'Trigger 4 - Validate number of signatures on the voter list',
     'description':
     str('Validate that the total number of received ballots equals the '
         'total of the ballots inside the box plus ballots outside the box. '
         'If the result form does not have a reconciliation form this trigger '
         'will always pass.'),
     'method': 'pass_signatures_validation',
     'active': False,
     'value': 2,
     'percentage': 0},
    {'name': 'Trigger 5 - Validate the total number of ballots inside the box',
     'description':
     str('The total number of ballot papers inside the ballot box will be '
         'compared against the total of valid, invalid, and unstamped ballots.'
         ' If the result form does not have a reconciliation form this trigger'
         ' will always pass. '
         'Fails if the value of the number of ballots inside box from the '
         'recon form does not equal the value of the recon property '
         'number of ballots inside the box with an N% tolerance.'),
     'method': 'pass_ballots_inside_box_validation',
     'active': False,
     'value': 2,
     'percentage': 0},
    {'name': 'Trigger 6 - Validate sum of votes distributed to all candidates',
     'description':
     str('The total votes for candidates should equal the valid ballots: '
         'after sorting the ballots inside the ballot box as valid and '
         'invalid, and unstamped. The above sum should equal the'
         ' sum of all candidates votes. '
         'If the result form does not have a reconciliation form this trigger '
         'will always pass. '
         'Fails if the value of the number of valid votes from the recon form '
         'does not equal the sum of all candidates votes from the result form '
         'with an N% tolerance.'),
     'method': 'pass_sum_of_candidates_votes_validation',
     'active': False,
     'value': 0,
     'percentage': 0},
    {'name': 'Trigger 7 - Validate percentage of invalid ballots',
     'description':
     str('Validate the percentage of invalid ballots. '
         'If the result form does not have a reconciliation form this trigger '
         'will always pass. '
         'Fails if the percentage of invalid ballots is greater than the this '
         'trigger percentage value.'),
     'method': 'pass_invalid_ballots_percentage_validation',
     'active': False,
     'value': 0,
     'percentage': 20},
    {'name': 'Trigger 8 - Validate turnout percentage',
     'description':
     str('Validate the turnout percentage. '
         'If the result form does not have a reconciliation form this trigger '
         'will always pass. '
         'If the station for this result form has an empty registrants field '
         'this trigger will always pass. '
         'Fails if the turnout percentage is greater than the this '
         'trigger percentage value.'),
     'method': 'pass_turnout_percentage_validation',
     'active': False,
     'value': 0,
     'percentage': 100},
    {'name':
     'Trigger 9 - Validate percentage of votes per candidate of total votes',
     'description':
     str('Validate that the percentage of votes per candidate of the total '
         'valid votes does not exceed a certain threshold. '
         'If the result form does not have a reconciliation form this trigger '
         'will always pass. '
         'Fails if the percentage of votes for a particular candidate '
         'of the total valid votes is greater than the this trigger '
         'percentage value.'),
     'method': 'pass_percentage_of_votes_per_candidate_validation',
     'active': False,
     'value': 0,
     'percentage': 50},
    {'name':
     'Trigger 10 - Validate percentage of blank ballots',
     'description':
     str('Validate the percentage of blank ballots. '
         'If the result form does not have a reconciliation form this trigger '
         'will always pass. '
         'Fails if the percentage of blank ballots is greater than the this '
         'trigger percentage value.'),
     'method': 'pass_percentage_of_blank_ballots_trigger',
     'active': False,
     'value': 0,
     'percentage': 20},
]

SUB_CONSTITUENCY_COLUMN_NAMES = ['SubCon #', 'Field Office', 'Races',
                                 'Ballot Number - General',
                                 'Ballot Number - Women', 'Number of Ballots',
                                 'Component Ballot', 'A4 Ballot', 'A3 Ballot',
                                 'A3 Folded Ballot', 'Ballot Size for General',
                                 'Ballot Size for Women',
                                 'Ballot Size for Consultation',
                                 'R&R Form Size - General',
                                 'R&R Form Size - Women',
                                 'R&R Form Size - Consultation',
                                 'R&R Form A3 Size', 'R&R Form A3 folded Size',
                                 'Screens Per Station',
                                 'Ballot Boxes Per Station']

CENTER_COLUMN_NAMES = ['#', 'Region/ المنطقة', 'PC Code/ رمز مركز الانتخاب',
                       'Office #/ الللجنة الانتخابية #',
                       'Office/ الللجنة الانتخابية ',
                       'Main C/ الدائرة الانتخابية الرئيسية',
                       'SubC # / رقم الدائرة الفرعية ',
                       'SubC name / الدائرة الفرعية', 'Name PC',
                       'Mahalla / المحلة',
                       'Village / المدينة/القرية', 'نوع المركز / Type',
                       'E  خط العرض   / Coordinates E',
                       'N  خط العرض   / Coordinates N']

STATION_COLUMN_NAMES = ['Centre #', 'Centre Name', 'SubCon #',
                        'Station number', 'Station Gender',
                        'Number of Registrants', 'First Name',
                        'First Name Number', 'Last Name', 'Last Name Number',
                        'When Generated']

RESULT_FORM_COLUMN_NAMES = ['Ballot Number', 'PC Code/ رمز مركز الانتخاب',
                            'Station', 'Gender', 'Name PC',
                            'Office/ الللجنة الانتخابية ',
                            'Office #/ الللجنة الانتخابية #',
                            'Bar Code Number', 'Serial Number']

CANDIDATE_COLUMN_NAMES = ['ID', 'Duplicate', 'Office_ID', 'E_Mail',
                          'Uploaded_Date_Time', 'Main_District_ID',
                          'Sub_District_ID', 'Voting_District', 'National_ID',
                          'Family_Book_ID', 'Name', 'Fathers_Name',
                          'G_Fathers_Name', 'Family_Name', 'Full_Name',
                          'Mothers_Name', 'Phone_Mobile', 'Land_Line',
                          'Race_Type', 'Gender_Type', 'Date_Of_Birth',
                          'Electoral_Camp_ID', 'Check_Family_Book',
                          'Check_ID', 'Check_IPC_Form', 'Check_Education_Cert',
                          'Check_Clearance_From_Moi', 'Check_Supporters_List',
                          'Check_Payment_Reset', 'Check_Bank_Account',
                          'Check_Two_Photos', 'Check_Code_Of_Conduct',
                          'Check_Signature', 'User_ID', 'Registration',
                          'Candidate_Number', 'Uploaded_By', 'Gender_En',
                          'Gender_Ar', 'Type_Of_Candidate_En',
                          'Type_Of_Candidate_Ar', 'Main_District_Ar',
                          'Main_District_En', 'Office_Name_Ar',
                          'Office_Name_En', 'Sub_District_Ar',
                          'Sub_District_En', 'Region']

BALLOT_ORDER_COLUMN_NAMES = ['ID', 'Ballot_Number']
