import os
from tally_ho.settings.common import *  # flake8: noqa

DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ['192.168.1.1', 'data-entry.ly', 'localhost']

os.environ.setdefault('DB_NAME', 'REPLACE_DB_NAME')
os.environ.setdefault('DB_USER', 'REPLACE_DB_USER')
os.environ.setdefault('DB_PASSWORD', 'REPLACE_DB_PASSWORD')
os.environ.setdefault('DB_HOST', 'REPLACE_DB_HOST')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME'),
        'USER':  os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST')
    }
}
