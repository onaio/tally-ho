from collections import OrderedDict

from django.conf import settings
from django.db.models import Q
from django.forms import ValidationError
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import get_matched_results
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.permissions import groups


def update_result_form_entries_with_de_errors(
    data_entry_1_errors, data_entry_2_errors, tally_id
):
    """Update result form stats entries that have DE errors.

    :param data_entry_1_errors: Number of errors caused by data entry 1 clerk.
    :param data_entry_2_errors: Number of errors caused by data entry 2 clerk.
    :param tally_id: ID of tally.
    """

    qs = ResultFormStats.objects.filter(
        result_form__tally__id=tally_id)

    if data_entry_1_errors:
        data_entry_1_result_form_stat =\
            qs.filter(
                Q(user__groups__name=groups.DATA_ENTRY_1_CLERK))\
            .order_by('-created_date').first()

        if data_entry_1_result_form_stat:
            data_entry_1_result_form_stat.data_entry_errors +=\
                data_entry_1_errors
            data_entry_1_result_form_stat.save()

    if data_entry_2_errors:
        data_entry_2_result_form_stat =\
            qs.filter(
                Q(user__groups__name=groups.DATA_ENTRY_2_CLERK))\
            .order_by('-created_date').first()

        if data_entry_2_result_form_stat:
            data_entry_2_result_form_stat.data_entry_errors +=\
                data_entry_2_errors
            data_entry_2_result_form_stat.save()


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


def get_candidates(results, num_results=None):
    """Return ordered tuples of candidates and their results.

    :param num_results: Enforce a particular number of results, default None.
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

    return [[c] + r[0:num_results] if num_results else r
            for c, r in candidates.items()]


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


def candidate_results_for_race_type(result_form, race_type, num_results=None):
    """Return the candidates and results for a result form and race type.

    :param result_form: The result form to return data for.
    :param race_type: The race type to get results for, get component results
        if this is None.
    :param num_results: Enforce a particular number of results, default None.

    :returns: A list of tuples containing the candidate and all results for
        that candidate.
    """
    return get_candidates(get_results_for_race_type(result_form, race_type),
                          num_results)


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
    no_match = get_matched_results(result_form, results)[1]

    if len(candidate_fields) != len(no_match):
        raise ValidationError(
            _(u"Please select correct results for all mis-matched votes."))

    changed_candidates = []
    de_1_suffix = getattr(settings, "DE_1_SUFFIX")
    de_2_suffix = getattr(settings, "DE_2_SUFFIX")

    post_data_has_corrections =\
        any(item.endswith(de_1_suffix) or item.endswith(de_2_suffix)
            for item in post_data)

    if post_data_has_corrections:
        # Update result form stats entries that required corrections
        update_result_form_entries_with_de_errors(
            de_1_suffix, de_2_suffix, post_data)

    for field in candidate_fields:
        number_of_times_to_call_replace = 2
        candidate_field = field

        # Remove DE1 and DE2 suffixes only when post_data has corrections
        if post_data_has_corrections:
            for n in range(number_of_times_to_call_replace):
                if candidate_field.endswith(de_1_suffix):
                    candidate_field = candidate_field.replace(de_1_suffix, '')
                if candidate_field.endswith(de_2_suffix):
                    candidate_field = candidate_field.replace(de_2_suffix, '')
                else:
                    candidate_field = candidate_field.replace(prefix, '')

        candidate_pk =\
            candidate_field\
            if post_data_has_corrections else field.replace(prefix, '')
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
                          user=user.userprofile)


def save_women_results(result_form, post_data, user):
    save_candidate_results_by_prefix('women', result_form, post_data,
                                     RaceType.WOMEN, user)
