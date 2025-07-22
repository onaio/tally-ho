from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.mixins import (DataTablesMixin, GroupRequiredMixin,
                                        TallyAccessMixin)


class ElectrolRaceListDataView(LoginRequiredMixin,
                       GroupRequiredMixin,
                       TallyAccessMixin,
                       BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ElectrolRace
    columns = (
        'election_level',
        'ballot_name',
        'active',
        'modified_date_formatted',
        'action',
    )

    def render_column(self, row, column):
        if column == 'action':
            return row.get_action_button
        else:
            return super(ElectrolRaceListDataView, self).render_column(
                row, column)

    def filter_queryset(self, qs):
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.GET.get('search[value]', None)

        if tally_id:
            qs = qs.filter(tally__id=tally_id)
        else:
            qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(Q(election_level__icontains=keyword)|
                           Q(ballot_name__icontains=keyword))

        return qs


class ElectrolRaceListView(LoginRequiredMixin,
                     GroupRequiredMixin,
                     TallyAccessMixin,
                     DataTablesMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/electrol_races.html"

    def get(self, *args, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        reverse_url = 'electrol-race-list-data'
        report_title = _('Electrol Races List')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                reverse_url,
                kwargs=kwargs),
            tally_id=tally_id,
            report_title=report_title,
))
