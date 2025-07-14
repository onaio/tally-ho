from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale, get_deployed_site_url)
from tally_ho.libs.views import mixins


class TallyListDataView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        BaseDatatableView):
    group_required = groups.TALLY_MANAGER
    model = Tally
    columns = (
        'id',
        'name',
        'created_date',
        'modified_date_formatted',
        'administer',
        'edit',
    )
    order_columns = (
        'id',
        'name',
        'created_date',
        'modified_date'
    )

    def render_column(self, row, column):
        if column == 'administer':
            return row.administer_button
        elif column == 'edit':
            return row.edit_button
        else:
            return super(TallyListDataView, self).render_column(row, column)

    def filter_queryset(self, qs):
        qs = qs.filter(active=True)
        keyword = self.request.POST.get('search[value]')

        if keyword:
            qs = qs.filter(Q(name__icontains=keyword))

        return qs


class TallyListView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "data/tallies.html"

    def get(self, *args, **kwargs):
        language_de = get_datatables_language_de_from_locale(self.request)
        additional_context = {
            "tally_id": None,
            'deployedSiteUrl': get_deployed_site_url(),
            'get_centers_stations_url': '/ajax/get-centers-stations/',
            "candidates_list_download_url": ("/ajax/download-"
                                "candidates-list/"),
            "enable_scroll_x": True,
            "enable_responsive": False,
            "centers_and_stations_list_download_url": ("/ajax/download-"
                                "centers-and-stations-list/"),
            "sub_cons_list_download_url": "/ajax/download-sub-cons-list/",
            "result_forms_download_url": "/ajax/download-result-forms/",
            ("centers_stations_by_mun_candidates"
                                "_votes_results_download_url"): (
                "/ajax/download-centers-stations"
                    "-by-mun-results-candidates-votes/"),
            "centers_by_mun_candidate_votes_results_download_url": (
                "/ajax/download-centers-"
                    "by-mun-results-candidates-votes/"),
            "get_export_url": "/ajax/get-export/",
            "offices_list_download_url": "/ajax/download-offices-list/",
            "regions_list_download_url": "/ajax/download-regions-list/",
            "centers_by_mun_results_download_url": (
                "/ajax/download-"
                    "centers-by-mun-results/"),
            "results_download_url": "/ajax/download-results/",
            "export_file_name": _("tally-list")
        }

        return self.render_to_response(self.get_context_data(
            remote_url='tally-list-data',
            languageDE=language_de, **additional_context))
