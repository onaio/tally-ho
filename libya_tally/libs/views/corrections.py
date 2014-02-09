from collections import OrderedDict

from django.forms import ValidationError
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.candidate import Candidate
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import get_matched_results
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.race_type import RaceType


def get_matched_forms(result_form):
    results_v1 = Result.objects.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_1)\
        .values('candidate', 'votes')
    results_v2 = Result.objects.filter(
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


def get_candidates(result_form, results=None):
    candidates = OrderedDict()
    if results is None:
        results = result_form.results

    last_race_type = None
    for result in results.order_by('candidate__race_type', 'candidate__order',
                                   'entry_version'):
        candidate = result.candidate
        race_type = candidate.race_type_name if\
            candidate.race_type != last_race_type else None
        last_race_type = candidate.race_type

        if candidate in candidates.keys():
            candidates[candidate].append(result)
        else:
            candidates.update({candidate: [race_type, result]})

    return candidates


def get_results_for_race_type(result_form, race_type):
    results = result_form.results.filter(candidate__race_type=race_type)
    candidates = get_candidates(result_form, results)

    return [[c] + r for c, r in candidates.iteritems()]


def save_candidate_results_by_prefix(prefix, result_form, post_data,
                                     race_type, user):
    prefix = 'candidate_%s_' % prefix

    candidate_fields = [f for f in post_data if f.startswith(prefix)]

    results = result_form.results.filter(candidate__race_type=race_type)
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
    results = Result.objects.filter(
        result_form=result_form,
        entry_version=EntryVersion.DATA_ENTRY_2)
    for result in results:
        save_result(result.candidate, result_form, EntryVersion.FINAL,
                    result.votes, user)


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
