from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class TurnOutListDataView(LoginRequiredMixin,
                          mixins.GroupRequiredMixin,
                          mixins.TallyAccessMixin,
                          BaseDatatableView):
    group_required = groups.TALLY_MANAGER
    model = ResultForm
    columns = (
        'office.name',
        'center.sub_constituency.code',
        'center.name',
        'center.code',
        'station_number',
        'gender',
        'reconciliationform.number_ballots_used',
    )

    def filter_queryset(self, qs):
        keyword = self.request.GET.get('search[value]', None)
        tally_id = self.kwargs['tally_id']
        qs = qs.filter(
            tally__id=tally_id,
            reconciliationform__isnull=False)\
            .exclude(form_state=FormState.UNSUBMITTED)\
            .order_by(
            'center__id', 'station_number', 'ballot__id')\
            .distinct(
            'center__id', 'station_number', 'ballot__id')

        if keyword:
            qs = qs.filter(Q(office__name__contains=keyword) |
                           Q(center__name__contains=keyword) |
                           Q(center__code__contains=keyword) |
                           Q(station_number__contains=keyword) |
                           Q(center__sub_constituency__code__contains=keyword))
        return qs

    def render_column(self, row, column):
        return super(TurnOutListDataView, self).render_column(row, column)


class TurnOutListView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.TallyAccessMixin,
                      TemplateView):
    group_required = groups.TALLY_MANAGER
    model = ResultForm
    template_name = "reports/turnout.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('turnout-list-data', kwargs=kwargs),
            tally_id=tally_id))
