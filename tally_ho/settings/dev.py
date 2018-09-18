from tally_ho.settings.common import *  # flake8: noqa


DEBUG = True

if DEBUG:
    INSTALLED_APPS += ('debug_toolbar',)

if DEBUG:
    MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

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
