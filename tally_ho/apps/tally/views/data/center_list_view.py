from django.views.generic import TemplateView
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.views.pagination import paging


class CenterListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.DatatablesDisplayFieldsMixin,
                         DatatablesView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    fields = (
        'center__office__name',
        'sub_constituency__code',
        'center__name',
        'center__code',
        'station_number',
        'gender',
        'registrants',
        'percent_received',
        'percent_archived',
    )
    display_fields = (
        ('center__office__name', 'center_office'),
        ('sub_constituency__code', 'sub_constituency_code'),
        ('center__name', 'center_name'),
        ('center__code', 'center_code'),
        ('station_number', 'station_number'),
        ('gender', 'gender_name'),
        ('registrants', 'registrants'),
        ('percent_received', 'percent_received'),
        ('percent_archived', 'percent_archived'),
    )


class CenterListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/centers.html"

    def get(self, *args, **kwargs):
        # check cache
        Station.update_cache()
        station_list = Station.objects.all()
        stations = paging(station_list, self.request)

        return self.render_to_response(self.get_context_data(
            stations=stations,
            remote_url='center-list-data'))
