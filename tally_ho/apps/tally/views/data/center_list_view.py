from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class CenterListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
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
        'center.active',
        'active',
    )


class CenterListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    template_name = "data/centers.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        format_ = kwargs.get('format')

        if format_ and format_ == 'csv':
            station_list = Station.objects.filter(center__tally__id=tally_id)

            station_list = station_list.values(
                'center__office__name',
                'sub_constituency__code',
                'center__name',
                'center__code',
                'station_number',
                'gender',
                'registrants',
                'percent_received',
                'percent_archived',
            ).order_by('center__code')

            header_map = {
                'center__office__name': 'office name',
                'sub_constituency__code': 'subconstituency code',
                'center__name': 'center name',
                'center__code': 'center code',
            }

            return render_to_csv_response(station_list,
                                          filename='centers_and_station',
                                          append_datestamp=True,
                                          field_header_map=header_map)

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('center-list-data', kwargs=kwargs),
            tally_id=tally_id))
