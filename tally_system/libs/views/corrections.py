from collections import OrderedDict

from django.forms import ValidationError
from django.utils.translation import ugettext as _

from tally_system.apps.tally.models.candidate import Candidate
from tally_system.apps.tally.models.result import Result
from tally_system.apps.tally.models.result_form import get_matched_results
from tally_system.libs.models.enums.entry_version import EntryVersion
from tally_system.libs.models.enums.race_type import RaceType


def get_matched_forms(result_form):
    """Return matches and not matching lists from data entry 1 and 2.

    :param result_form: The result form to fetch data from.

    :returns: A list of matches and a list is mismatches.
    """
    results_v1 = Result.objects.filter(
        active=True,
        result_form=result_form,
        entry_version=EntryVersion.DATA_ENTRY_1).values('candidate', 'votes')
    results_v2 = Result.objects.filter(
        active=True,
        result_form=result_form,
        entry_version=EntryVersion.DATA_ENTRY_2).values('candidate', 'votes')

    if not results_v1 or not results_v2:
        raise Exception(_(u"Result Form has no double entries."))

    if results_v1.count() != results_v2.count():
        return False

    tuple_list = [i.items() for i in results_v1]
    matches = [rec for rec in results_v2 if rec.items() in tuple_list]
    no_match = [rec for rec in results_v2 if rec.items() not in tuple_list]

    return matches, no_match


def get_candidates(results):
    """Return ordered tuples of candidates and their results.

    :param results: The results to get candidates from.

    :returns: A list of tuples of candidates and the results associated with
        them.
    """
    candidates = OrderedDict()

    for result in results.order_by('candidate__race_type', 'candidate__order',
                                   'entry_version'):
        candidate = result.candidate

        if candidates.get(candidate):
            candidates[candidate].append(result)
        else:
            candidates.update({candidate: [result]})

    return [[c] + r for c, r in candidates.iteritems()]


def get_results_for_race_type(result_form, race_type):
    """Return the results for a result form and race type.

    :param result_form: The result form to return data for.
    :param race_type: The race type to get results for, get component results
        if this is None.

    :returns: A queryset of results.
    """
    results = result_form.results.filter(active=True)

    return results.filter(candidate__race_type__gt=RaceType.WOMEN) if\
        race_type is None else results.filter(candidate__race_type=race_type)


def candidate_results_for_race_type(result_form, race_type):
    """Return the candidates and results for a result form and race type.

    :param result_form: The result form to return data for.
    :param race_type: The race type to get results for, get component results
        if this is None.

    :returns: A list of tuples containing the candidate and all results for
        that candidate.
    """
    return get_candidates(get_results_for_race_type(result_form, race_type))


def save_candidate_results_by_prefix(prefix, result_form, post_data,
                                     race_type, user):
    """Fetch fields from post_data based on prefix and save final results for
    them.

    :param prefix: The prefix to search for in the post data.
    :param result_form: The result form to save final results for.
    :param post_data: The data to pull candidate values from.
    :param race_type: The race type to fetch results for.
    :param user: The user to associate with the final results.

    :raises: `ValidationError` if a selection is not found for every mismatched
        candidate.
    """
    prefix = 'candidate_%s_' % prefix

    candidate_fields = [f for f in post_data if f.startswith(prefix)]
    results = get_results_for_race_type(result_form, race_type)
    matches, no_match = get_matched_results(result_form, results)

    if len(candidate_fields) != len(no_match):
        raise ValidationError(
            _(u"Please select correct results for all mis-matched votes."))

    changed_candidates = []

    for field in candidate_fields:
        candidate_pk = field.replace(prefix, '')
        candidate = Candidate.objects.get(pk=candidate_pk)
        votes = post_data[field]
        save_result(candidate, result_form, EntryVersion.FINAL, votes, user)
        changed_candidates.append(candidate)

    results_v2 = results.filter(result_form=result_form,
                                entry_version=EntryVersion.DATA_ENTRY_2)

    for result in results_v2:
        if result.candidate not in changed_candidates:
            save_result(result.candidate, result_form, EntryVersion.FINAL,
                        result.votes, user)


def save_final_results(result_form, user):
    """Save final results based on existing results.

    :param result_form: The result form to save final results for.
    :param user: The user to associate final results with.
    """
    results = Result.objects.filter(
        result_form=result_form,
        entry_version=EntryVersion.DATA_ENTRY_2, active=True)

    for result in results:
        save_result(result.candidate, result_form, EntryVersion.FINAL,
                    result.votes, user)


def save_component_results(result_form, post_data, user):
    save_candidate_results_by_prefix('component', result_form, post_data,
                                     None, user)


def save_general_results(result_form, post_data, user):
    save_candidate_results_by_prefix('general', result_form, post_data,
                                     RaceType.GENERAL, user)


def save_result(candidate, result_form, entry_version, votes, user):
    Result.objects.create(candidate=candidate,
                          result_form=result_form,
                          entry_version=entry_version,
                          votes=votes,
                          user=user)


def save_women_results(result_form, post_data, user):
    save_candidate_results_by_prefix('women', result_form, post_data,
                                     RaceType.WOMEN, user)
