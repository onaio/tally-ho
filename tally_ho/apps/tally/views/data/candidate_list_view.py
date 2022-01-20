import json

from django.db.models import Q, F
from django.views.generic import TemplateView
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.http import JsonResponse
from guardian.mixins import LoginRequiredMixin
from django.utils import timezone

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.libs.reports.progress import get_office_candidates_ids
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.models.enums.race_type import RaceType


class CandidateListDataView(LoginRequiredMixin,
                            mixins.GroupRequiredMixin,
                            mixins.TallyAccessMixin,
                            BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Candidate
    columns = (
        'candidate_id',
        'full_name',
        'active',
        'order',
        'ballot.number',
        'race_type',
        'modified_date_formatted',
        'action',
    )

    def render_column(self, row, column):
        if column == 'action':
            return row.get_action_button
        else:
            return super(CandidateListDataView, self).render_column(
                row, column)

    def filter_queryset(self, qs):
        tally_id = self.kwargs.get('tally_id')
        office_id = self.kwargs.get('office_id')
        keyword = self.request.GET.get('search[value]', None)

        if tally_id:
            if office_id:
                candidate_ids = get_office_candidates_ids(office_id=office_id,
                                                          tally_id=tally_id)
                qs = qs.filter(tally__id=tally_id, pk__in=candidate_ids)
            else:
                qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(Q(full_name__contains=keyword))

        return qs


class CandidateListView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/candidates.html"

    def get(self, *args, **kwargs):
        # check cache
        tally_id = self.kwargs.get('tally_id')
        office_id = self.kwargs.get('office_id')
        reverse_url = 'candidate-list-data'
        report_title = _('Candidate List')

        if office_id:
            reverse_url = 'candidate-list-data-per-office'
            report_title = _('Candidate List Per Office')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                reverse_url,
                kwargs=kwargs),
            tally_id=tally_id,
            report_title=report_title,
            candidates_list_download_url='/ajax/download-candidates-list/'))


def get_candidates_list(request):
    """
    Builds a json object of candidates list.

    :param request: The request object containing the tally id.

    returns: A JSON response of candidates list
    """
    tally_id = json.loads(request.GET.get('data')).get('tally_id')
    candidates_list = Candidate.objects.filter(tally__id=tally_id)\
        .annotate(ballot_number=F('ballot__number'),)\
        .values(
            'candidate_id',
            'full_name',
            'active',
            'order',
            'ballot_number',
            'race_type',
    )
    for candidate in candidates_list:
        if isinstance(candidate['race_type'], RaceType):
            candidate['race_type'] = candidate['race_type'].name

    return JsonResponse(
        data={'data': list(candidates_list), 'created_at': timezone.now()},
        safe=False)
