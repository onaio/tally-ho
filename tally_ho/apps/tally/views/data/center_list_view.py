from django.views.generic import TemplateView
from django.core.urlresolvers import reverse

from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin
from djqscsv import render_to_csv_response

from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.views.pagination import paging


class CenterListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
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
        'center__active',
        'active',
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
        ('center__active', 'center_status'),
        ('active', 'station_status'),
        # Used to add external columns to the table.
        ('active', 'get_edit_links'),
    )

    def get_queryset(self):
        qs = super(CenterListDataView, self).get_queryset()
        tally_id = self.kwargs.get('tally_id')

        if tally_id:
            qs = qs.filter(center__tally__id=tally_id)

        return qs

    def render_to_response(self, form, **kwargs):
        '''Render Datatables expected JSON format'''
        page = self.get_page(form)

        Station.update_percentages(page.object_list)

        data = {
            'iTotalRecords': page.paginator.count,
            'iTotalDisplayRecords': page.paginator.count,
            'sEcho': form.cleaned_data['sEcho'],
            'aaData': self.get_rows(page.object_list),
        }

        return self.json_response(data)


class CenterListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/centers.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        format_ = kwargs.get('format')

        if format_ and format_ == 'csv':
            station_list = Station.objects.filter(center__tally__id=tally_id)

            station_list = station_list.values(
                    'center__office__name', 'sub_constituency__code',
                    'center__name', 'center__code', 'station_number',
                    'gender', 'registrants', 'percent_received',
                    'percent_archived',).order_by('center__code')

            header_map = {'center__office__name': 'office name',
                    'sub_constituency__code': 'subconstituency code',
                    'center__name': 'center name',
                    'center__code': 'center code',}

            return render_to_csv_response(station_list,
                    filename='centers_and_station',
                    append_datestamp=True,
                    field_header_map=header_map)

        # check cache
        station_list = Station.objects.filter(center__tally__id=tally_id)
        stations = paging(station_list, self.request)

        return self.render_to_response(self.get_context_data(
            stations=stations,
            remote_url=reverse('center-list-data', kwargs=kwargs),
            tally_id=tally_id))
