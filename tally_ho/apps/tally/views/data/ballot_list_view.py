from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.mixins import (DataTablesMixin, GroupRequiredMixin,
                                        TallyAccessMixin)


class BallotListDataView(LoginRequiredMixin,
                       GroupRequiredMixin,
                       TallyAccessMixin,
                       BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Ballot
    columns = (
        'number',
        'active',
        'electrol_race.election_level',
        'electrol_race.ballot_name',
        'modified_date_formatted',
        'available_for_release',
        'action',
    )

    def render_column(self, row, column):
        if column == 'action':
            return row.get_action_button
        else:
            return super(BallotListDataView, self).render_column(
                row, column)

    def filter_queryset(self, qs):
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.POST.get('search[value]', None)

        if tally_id:
            qs = qs.filter(tally__id=tally_id)
        else:
            qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(Q(number__contains=keyword)|
                           Q(electrol_race__election_level__icontains=keyword))

        return qs


class BallotListView(LoginRequiredMixin,
                     GroupRequiredMixin,
                     TallyAccessMixin,
                     DataTablesMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/ballots.html"

    def get(self, *args, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        reverse_url = 'ballot-list-data'
        report_title = _('Ballot List')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                reverse_url,
                kwargs=kwargs),
            tally_id=tally_id,
            report_title=report_title, export_file_name='ballots',
            server_side=True,
        ))
