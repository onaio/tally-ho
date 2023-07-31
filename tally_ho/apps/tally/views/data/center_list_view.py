import json

from django.db.models import Q, F
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone

from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale
)
from tally_ho.libs.views import mixins


class CenterListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
                         BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    columns = (
        'center.office.name',
        'sub_constituency.name',
        'sub_constituency.code',
        'center.office.region.name',
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
        keyword = self.request.POST.get('search[value]')
        tally_id = self.kwargs.get('tally_id')
        region_id = self.kwargs.get('region_id')
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
                           Q(sub_constituency__name__contains=keyword) |
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
        region_id = kwargs.get('region_id')
        constituency_id = kwargs.get('constituency_id')
        sub_constituency_id = kwargs.get('sub_constituency_id')
        format_ = kwargs.get('format')
        language_de = get_datatables_language_de_from_locale(self.request)
        download_url = '/ajax/download-centers-and-stations-list/'

        try:
            region_name = region_id and Region.objects.get(
                tally__id=tally_id, id=region_id).name
        except Region.DoesNotExist:
            region_name = None

        try:
            constituency_name =\
                constituency_id and Constituency.objects.get(
                    id=constituency_id,
                    tally__id=tally_id).name
        except Constituency.DoesNotExist:
            constituency_name = None

        try:
            sub_constituency_code =\
                sub_constituency_id and SubConstituency.objects.get(
                    id=sub_constituency_id,
                    tally__id=tally_id).code
        except SubConstituency.DoesNotExist:
            sub_constituency_code = None

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
            sub_constituency_code=sub_constituency_code,
            centers_and_stations_list_download_url=download_url,
            languageDE=language_de
        ))


def get_centers_stations_list(request):
    """
    Builds a json object of centers and stations list.

    :param request: The request object containing the tally id.

    returns: A JSON response of centers and stations list
    """
    tally_id = json.loads(request.GET.get('data')).get('tally_id')
    centers_stations_list = Station.objects.filter(center__tally__id=tally_id)\
        .annotate(
            center_name=F('center__name'),
            center_code=F('center__code'),
            office_id=F('center__office__id'),
            office_name=F('center__office__name'),
            office_number=F('center__office__number'),
            sub_constituency_code=F('sub_constituency__code'),
            region_id=F('center__office__region__id'),
            region_name=F('center__office__region__name'),
            station_id=F('id'))\
        .values(
            'region_id',
            'region_name',
            'office_id',
            'office_name',
            'sub_constituency_code',
            'center_code',
            'center_name',
            'station_id',
            'station_number',
            'registrants',
            'percent_received',
            'percent_archived',
        ).order_by('center__code')

    return JsonResponse(
        data={
            'data': list(centers_stations_list),
            'created_at': timezone.now()
        },
        safe=False)
