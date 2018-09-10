from django.core import validators


class MinLengthValidator(validators.MinLengthValidator):
    def clean(self, x):
        return len(u"%s" % x)
