import json

from django.urls import reverse
from django.views.generic import TemplateView
from django.db.models import F

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin
from django.http import JsonResponse

from tally_ho.apps.tally.models.office import Office
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class OfficeListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
                         BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Office
    columns = (
        'id',
        'name',
        'number',
        'region.name',
    )

    def filter_queryset(self, qs):
        keyword = self.request.GET.get('search[value]', None)
        tally_id = self.kwargs.get('tally_id')

        qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(name__contains=keyword)
        return qs

    def render_column(self, row, column):
        return super(OfficeListDataView, self).render_column(row, column)


class OfficeListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Office
    template_name = "data/offices.html"

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('office-list-data', kwargs=kwargs),
            tally_id=tally_id,
            offices_list_download_url='/ajax/download-offices-list/'
        ))


def get_offices_list(request):
    """
    Builds a json object of offices list.

    :param request: The request object containing the tally id.

    returns: A JSON response of offices list
    """
    tally_id = json.loads(request.GET.get('data')).get('tally_id')
    offices_list = Office.objects.filter(tally__id=tally_id)\
        .annotate(
            region_name=F('region__name'))\
        .values(
            'id',
            'name',
            'number',
            'region_id',
            'region_name',
    )

    return JsonResponse(list(offices_list), safe=False)
