from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class TurnOutListDataView(LoginRequiredMixin,
                          mixins.GroupRequiredMixin,
                          mixins.TallyAccessMixin,
                          BaseDatatableView):
    group_required = groups.TALLY_MANAGER
    model = Station
    columns = (
        'station_number',
        'gender',
        'registrants',
        'num_ballots_used',
        'percentage_turn_out',
    )
    order_columns = (
        'station_number',
        'gender',
        'registrants',
    )

    def filter_queryset(self, qs):
        keyword = self.request.GET.get('search[value]', None)
        tally_id = self.kwargs['tally_id']
        qs = qs.filter(tally__id=tally_id).exclude(registrants__isnull=True)

        if keyword:
            qs = qs.filter(Q(station_number__contains=keyword) |
                           Q(registrants__contains=keyword))
        return qs

    def render_column(self, row, column):
        return super(TurnOutListDataView, self).render_column(row, column)


class TurnOutListView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.TallyAccessMixin,
                      TemplateView):
    group_required = groups.TALLY_MANAGER
    model = Station
    template_name = "reports/turnout.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('turnout-list-data', kwargs=kwargs),
            tally_id=tally_id))
