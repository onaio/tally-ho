from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class StationProgressListDataView(LoginRequiredMixin,
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
        'active',
    )

    def filter_queryset(self, qs):
        tally_id = self.kwargs['tally_id']
        station_pks = ResultForm.objects.filter(
            form_state=FormState.ARCHIVED,
            tally__id=tally_id
        ).values_list('station_number', flat=True)

        qs = qs.filter(station_number__in=station_pks, tally__id=tally_id)

        keyword = self.request.GET.get('search[value]', None)

        if keyword:
            qs = qs.filter(Q(station_number__contains=keyword) |
                           Q(center__office__name__contains=keyword) |
                           Q(center__code__contains=keyword) |
                           Q(sub_constituency__code__contains=keyword) |
                           Q(center__name__contains=keyword))
        return qs

    def render_column(self, row, column):
        return super(
            StationProgressListDataView, self).render_column(row, column)


class StationProgressListView(LoginRequiredMixin,
                              mixins.GroupRequiredMixin,
                              mixins.TallyAccessMixin,
                              TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    template_name = "reports/station_progress.html"

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('staion-progress-list-data', kwargs=kwargs),
            tally_id=tally_id))
