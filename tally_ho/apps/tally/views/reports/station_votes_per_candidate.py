from django.db.models import Q, Sum
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.result import Result
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class StationVotesPerCandidateListDataView(LoginRequiredMixin,
                                           mixins.GroupRequiredMixin,
                                           mixins.TallyAccessMixin,
                                           BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Result
    columns = (
        'candidate__full_name',
        'total_votes_per_candidate',
    )
    order_columns = (
        'total_votes_per_candidate',
    )

    def filter_queryset(self, qs):
        tally_id = self.kwargs['tally_id']
        station_number = self.kwargs['station_number']
        qs =\
            qs.filter(active=True,
                      entry_version=EntryVersion.FINAL,
                      votes__gt=0,
                      result_form__tally_id=tally_id,
                      result_form__station_number=station_number)\
            .values('candidate__full_name')\
            .annotate(total_votes_per_candidate=Sum('votes'))

        keyword = self.request.GET.get('search[value]', None)

        if keyword:
            qs = qs.filter(Q(candidate__full_name=keyword))
        return qs

    def render_column(self, row, column):
        if column == 'candidate__full_name':
            return str('<td class="center sorting_1">'
                       f'{row["candidate__full_name"]}</td>')
        elif column == 'total_votes_per_candidate':
            return str('<td class="center">'
                       f'{row["total_votes_per_candidate"]}</td>')
        else:
            return super(
                StationVotesPerCandidateListDataView, self).render_column(
                row, column)


class StationVotesPerCandidateListView(LoginRequiredMixin,
                                       mixins.GroupRequiredMixin,
                                       mixins.TallyAccessMixin,
                                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Result
    template_name = "reports/station_votes_per_candidate.html"

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        station_number = kwargs.get('station_number')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                'staion-votes-per-candidate-list-data', kwargs=kwargs),
            tally_id=tally_id,
            station_number=station_number))
