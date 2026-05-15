from tally_ho.settings.common import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'db1',
        'USER': 'db1_role',
        'PASSWORD': 'db1_password',
        'HOST': 'db1',
        'PORT': 5432,
    }
}

CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'cache+memcached://memcached:11211/'

SITE_NAME = '[DEMO] Tally Ho - HNEC RMS'
