from django.forms.utils import ErrorList


def add_generic_error(form, message):
    errors = form._errors.setdefault("__all__", ErrorList())
    errors.append(message)

    return form
