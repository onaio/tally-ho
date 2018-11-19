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
