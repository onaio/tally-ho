import ast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView

from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.views.reports.administrative_areas_reports import \
    build_stations_centers_and_sub_cons_list
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.exports import build_candidate_results_output
from tally_ho.libs.views.mixins import (DataTablesMixin, GroupRequiredMixin,
                                        TallyAccessMixin)


def get_candidate_results_queryset(tally_id, data=None):
    """
    Returns a list of dicts, each representing a candidate result row,
    similar to the output of save_barcode_results.
    If data is None, include all forms for the tally.
    """
    from django.db.models import Prefetch
    from tally_ho.apps.tally.models.candidate import Candidate
    from tally_ho.apps.tally.models.result import Result
    from tally_ho.libs.models.enums.entry_version import EntryVersion

    queryset = []

    # Prefetch candidates with their results to eliminate N+1 queries
    candidates_prefetch = Prefetch(
        'ballot__candidates',
        queryset=Candidate.objects.select_related('ballot').prefetch_related(
            Prefetch(
                'results',
                queryset=Result.objects.filter(
                    entry_version=EntryVersion.FINAL,
                    active=True,
                    result_form__form_state=FormState.ARCHIVED,
                ),
                to_attr='final_results'
            )
        )
    )

    result_forms = ResultForm.objects.select_related(
        'ballot',
        'center',
        'center__office',
        'center__sub_constituency',
        'ballot__electrol_race',
    ).prefetch_related(
        candidates_prefetch,
        'center__stations',  # For result_form.station property
        'reconciliationform_set',  # For result_form.reconciliationform property
    ).filter(
        tally__id=tally_id,
        form_state=FormState.ARCHIVED,
    )
    if data:
        sub_con_codes = data.get('sub_con_codes') or []
        election_level_names = data.get('election_level_names') or []
        sub_race_type_names = data.get('sub_race_type_names') or []
        if sub_con_codes:
            result_forms = result_forms.filter(
                center__sub_constituency__code__in=sub_con_codes
            )
        if election_level_names:
            result_forms = result_forms.filter(
                ballot__electrol_race__election_level__in=
                election_level_names
            )
        if sub_race_type_names:
            result_forms = result_forms.filter(
                ballot__electrol_race__ballot_name__in=sub_race_type_names
            )

    for result_form in result_forms:
        output = build_candidate_results_output(result_form)
        for candidate in result_form.ballot.candidates.all():
            row = output.copy()
            # Calculate votes from prefetched final_results instead of triggering new query
            votes = sum(result.votes for result in candidate.final_results
                       if result.result_form_id == result_form.id)
            row['order'] = candidate.order
            row['candidate_name'] = candidate.full_name
            row['candidate_id'] = candidate.candidate_id
            row['votes'] = votes
            row['race_number'] = candidate.ballot.number
            row['candidate_status'] = (
                'enabled' if candidate.active else 'disabled'
            )
            queryset.append(row)
    sorted_queryset = sorted(queryset, key=lambda x: -x['votes'])
    return sorted_queryset


class CandidateResultsDataView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    BaseDatatableView,
):
    group_required = groups.TALLY_MANAGER
    columns = [
        'ballot',
        'race_number',
        'center',
        'office',
        'station',
        'gender',
        'barcode',
        'election_level',
        'sub_race_type',
        'voting_district',
        'order',
        'candidate_name',
        'candidate_id',
        'votes',
        'invalid_ballots',
        'number_of_voter_cards_in_the_ballot_box',
        'received_ballots_papers',
        'valid_votes',
        'number_registrants',
        'candidate_status',
    ]
    order_columns = columns

    def get_initial_queryset(self, data=None):
        tally_id = self.kwargs.get('tally_id')
        return get_candidate_results_queryset(tally_id, data)

    def get(self, request, *args, **kwargs):
        request_data = request.GET.get('data')
        data = None
        if request_data:
            data = ast.literal_eval(request_data)
        queryset = self.get_initial_queryset(data)
        total_records = len(queryset)
        page = request.GET.get('start', 0)
        page_size = request.GET.get('length', 10)
        search = request.GET.get('search[value]', None)

        # Filtering
        if search:
            queryset = [
                row for row in queryset
                if search.lower() in str(row).lower()
            ]
            total_records = len(queryset)

        # Paging
        if page_size == '-1':
            page_records = queryset
        else:
            page_records = queryset[
                int(page):int(page) + int(page_size)
            ]

        response_data = JsonResponse({
            'draw': int(request.GET.get('draw', 0)),
            'recordsTotal': total_records,
            'recordsFiltered': total_records,
            'data': page_records,
        })
        return response_data


class CandidateResultsView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    DataTablesMixin,
    TemplateView,
):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/candidate_results.html'

    def get(self, request, *args, **kwargs):
        columns = (
            'ballot',
            'race_number',
            'center',
            'office',
            'station',
            'gender',
            'barcode',
            'election_level',
            'sub_race_type',
            'voting_district',
            'order',
            'candidate_name',
            'candidate_id',
            'votes',
            'invalid_ballots',
            'number_of_voter_cards_in_the_ballot_box',
            'received_ballots_papers',
            'valid_votes',
            'number_registrants',
            'candidate_status',
        )
        dt_columns = [{'data': column} for column in columns]
        tally_id = self.kwargs.get('tally_id')
        _, _, sub_cons = build_stations_centers_and_sub_cons_list(tally_id)
        electrol_races = ElectrolRace.objects.filter(tally__id=tally_id)
        context_data = {
            'tally_id': tally_id,
            'remote_url': reverse(
                'candidate-results-data',
                kwargs={'tally_id': kwargs.get('tally_id')},
            ),
            'sub_cons': sub_cons,
            'election_level_names': set(
                electrol_races.values_list('election_level', flat=True)
            ),
            'sub_race_type_names': set(
                electrol_races.values_list('ballot_name', flat=True)
            ),
            'dt_columns': dt_columns,
        }
        return self.render_to_response(self.get_context_data(**context_data))
