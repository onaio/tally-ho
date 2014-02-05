from django.core.exceptions import SuspiciousOperation
from django.utils.translation import ugettext as _
from libya_tally.libs.models.enums.entry_version import EntryVersion


def session_matches_post_result_form(post_data, request):
    pk = request.session.get('result_form')

    if 'result_form' not in post_data:
        raise SuspiciousOperation(_(u"Error: Missing result form!"))
    elif int(post_data['result_form']) != pk:
        raise SuspiciousOperation(
            _(u"Session result_form does not match submitted data."))

    return pk


def get_matched_results(result_form, results):
    results_v1 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_1)\
        .values('candidate', 'votes')
    results_v2 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_2)\
        .values('candidate', 'votes')

    if not results_v1 or not results_v2:
        raise Exception(_(u"Result Form has no double entries."))

    if results_v1.count() != results_v2.count():
        return False

    tuple_list = [i.items() for i in results_v1]
    matches = [rec for rec in results_v2 if rec.items() in tuple_list]
    no_match = [rec for rec in results_v2 if rec.items() not in tuple_list]

    return matches, no_match


def match_results(result_form, results=None):
    matches, no_match = get_matched_results(result_form, results)
    return len(no_match) == 0
