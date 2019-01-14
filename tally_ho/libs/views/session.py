from django.core.exceptions import SuspiciousOperation
from django.utils.translation import ugettext as _


def session_matches_post_result_form(post_data, request):
    """Verify that result form in post data matches session data.

    :param post_data: The post data to retrieve the result form key from.
    :param request: The request to retrieve the session result form key from.

    :raises: `SuspiciousOperation` if the session and form keys do not match.

    :returns: The result form private key.
    """
    pk = request.session.get('result_form')

    try:
        if 'result_form' not in post_data:
            raise SuspiciousOperation(_(u"Error: Missing result form!"))
        elif int(post_data['result_form']) != pk:
            raise SuspiciousOperation(
                _(u"Session result_form does not match submitted data."))
    except ValueError:
        raise SuspiciousOperation(_(u"Error: Missing result form!"))

    return pk
