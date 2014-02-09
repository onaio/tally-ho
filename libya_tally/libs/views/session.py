from django.core.exceptions import SuspiciousOperation
from django.utils.translation import ugettext as _


def session_matches_post_result_form(post_data, request):
    pk = request.session.get('result_form')

    if 'result_form' not in post_data:
        raise SuspiciousOperation(_(u"Error: Missing result form!"))
    elif int(post_data['result_form']) != pk:
        raise SuspiciousOperation(
            _(u"Session result_form does not match submitted data."))

    return pk
