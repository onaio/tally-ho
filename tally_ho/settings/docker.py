"""Demo / dev settings for the docker-compose stack.

NOT for production. This module:

- enables ``DEBUG=True``
- points at the in-network postgres / redis / memcached service hostnames
- trusts ``http://localhost:<TALLY_HO_HTTP_PORT>`` for CSRF

Production deployments should run their own settings module that
inherits ``tally_ho.settings.common`` and keeps ``DEBUG=False``.
"""
import os

from tally_ho.settings.common import *  # noqa

DEBUG = True

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

# Trust the host port the nginx container is bound to so POSTs pass CSRF.
_http_port = os.environ.get('TALLY_HO_HTTP_PORT', '8000')
CSRF_TRUSTED_ORIGINS = [
    f'http://localhost:{_http_port}',
    f'http://127.0.0.1:{_http_port}',
]

SITE_NAME = '[DEMO] Tally Ho - HNEC RMS'
