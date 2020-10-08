from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
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
        'edit',
    )

    def filter_queryset(self, qs):
        keyword = self.request.GET.get('search[value]', None)
        tally_id = self.kwargs.get('tally_id')
        region_id = self.kwargs.get('region_id', None)
        station_ids = self.request.session.get(
            'station_ids')

        qs = qs.filter(center__tally__id=tally_id)

        if station_ids and region_id:
            qs =\
                qs.filter(id__in=station_ids)
        elif station_ids and not region_id:
            del self.request.session['station_ids']

        if keyword:
            qs = qs.filter(Q(station_number__contains=keyword) |
                           Q(center__office__name__contains=keyword) |
                           Q(center__code__contains=keyword) |
                           Q(sub_constituency__code__contains=keyword) |
                           Q(center__name__contains=keyword))
        return qs

    def render_column(self, row, column):
        if column == 'edit':
            return row.get_edit_links
        else:
            return super(CenterListDataView, self).render_column(row, column)


class CenterListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    template_name = "data/centers.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        region_id = kwargs.get('region_id', None)
        constituency_id = kwargs.get('constituency_id', None)
        sub_constituency_id = kwargs.get('sub_constituency_id', None)
        format_ = kwargs.get('format')
        region_name = None
        constituency_name = None
        sub_constituency_code = None

        if region_id:
            region_name = Region.objects.get(id=region_id).name

        if constituency_id:
            constituency_name = Constituency.objects.get(
                id=constituency_id).name

        if sub_constituency_id:
            sub_constituency_code = SubConstituency.objects.get(
                id=sub_constituency_id).code

        if format_ == 'csv':
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
            tally_id=tally_id,
            region_name=region_name,
            constituency_name=constituency_name,
            sub_constituency_code=sub_constituency_code
        ))
