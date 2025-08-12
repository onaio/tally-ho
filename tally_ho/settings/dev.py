import os

from tally_ho.settings.common import *  # noqa
from tally_ho.settings.common import INSTALLED_APPS, MIDDLEWARE

INSTALLED_APPS += ('django_extensions',)

DEBUG = True

if DEBUG:
    INSTALLED_APPS += ('debug_toolbar',)

if DEBUG:
    MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

GRAPH_MODELS = {
    'all_applications': True,
    'group_models': True,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else os.getenv(
                'DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}
