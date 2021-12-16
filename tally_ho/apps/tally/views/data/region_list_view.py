import json

from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin
from django.http import JsonResponse

from tally_ho.apps.tally.models.region import Region
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class RegionListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
                         BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Region
    columns = (
        'id',
        'name',
    )

    def filter_queryset(self, qs):
        keyword = self.request.GET.get('search[value]', None)
        tally_id = self.kwargs.get('tally_id')

        qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(name__contains=keyword)
        return qs

    def render_column(self, row, column):
        return super(RegionListDataView, self).render_column(row, column)


class RegionListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Region
    template_name = "data/regions.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('office-list-data', kwargs=kwargs),
            tally_id=tally_id,
            regions_list_download_url='/ajax/download-regions-list/'
        ))


def get_regions_list(request):
    """
    Builds a json object of regions list.

    :param request: The request object containing the tally id.

    returns: A JSON response of regions list
    """
    tally_id = json.loads(request.GET.get('data')).get('tally_id')
    regions_list = Region.objects.filter(tally__id=tally_id)\
        .values(
            'id',
            'name',
    )

    return JsonResponse(list(regions_list), safe=False)
