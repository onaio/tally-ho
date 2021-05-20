from django.db.models import Q, Sum
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.result import Result
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class VotesPerCandidateListDataView(LoginRequiredMixin,
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

        qs = qs.filter(active=True,
                       entry_version=EntryVersion.FINAL,
                       votes__gt=0,
                       result_form__tally_id=tally_id)

        station_number = self.kwargs.get('station_number')
        center_code = self.kwargs.get('center_code')

        if station_number:
            qs = qs.filter(result_form__station_number=station_number)

        if center_code:
            qs = qs.filter(result_form__center__code=center_code)

        qs = qs\
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
                VotesPerCandidateListDataView, self).render_column(
                row, column)


class VotesPerCandidateListView(LoginRequiredMixin,
                                mixins.GroupRequiredMixin,
                                mixins.TallyAccessMixin,
                                TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Result
    template_name = "reports/votes_per_candidate.html"

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        station_number = kwargs.get('station_number')
        center_code = kwargs.get('center_code')
        report_name = None

        if station_number:
            report_name = _('Station')

        if center_code:
            report_name = _('Center')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                'votes-per-candidate-list-data', kwargs=kwargs),
            tally_id=tally_id,
            station_number=station_number,
            center_code=center_code,
            report_name=report_name))
