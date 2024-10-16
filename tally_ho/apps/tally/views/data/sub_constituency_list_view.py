from django.db.models import Q
from django.views.generic import TemplateView
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale
)
from tally_ho.libs.views import mixins


class SubConstituencyListDataView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = SubConstituency
    columns = (
        'code',
        'name',
        'number_of_ballots',
        'constituency.name',
    )

    def render_column(self, row, column):
        return super(SubConstituencyListDataView, self).render_column(
                row, column)


    def filter_queryset(self, qs):
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.POST.get('search[value]')

        if tally_id:
            qs = qs.filter(tally__id=tally_id)
        else:
            qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(Q(name__contains=keyword)|
                           Q(constituency__name__contains=keyword))

        return qs


class SubConstituencyListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/sub_cons_list.html"

    def get(self, *args, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        reverse_url = 'sub-cons-list-data'
        report_title = _('Sub Constituencies List')
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                reverse_url,
                kwargs=kwargs),
            tally_id=tally_id,
            report_title=report_title,
            sub_cons_list_download_url='/ajax/download-sub-cons-list/',
            languageDE=language_de))
