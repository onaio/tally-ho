from django.core import validators


class MinLengthValidator(validators.MinLengthValidator):
    clean = lambda self, x: len(u"%s" % x)
