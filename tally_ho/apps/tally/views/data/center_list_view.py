from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class CenterListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    columns = (
        'center.office.name',
        'sub_constituency.code',
        'center.name',
        'center.code',
        'station_number',
        'gender',
        'registrants',
        'percent_received',
        'percent_archived',
    )


class CenterListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    template_name = "data/centers.html"

    def get(self, *args, **kwargs):
        return self.render_to_response(self.get_context_data(
            remote_url='center-list-data'))
