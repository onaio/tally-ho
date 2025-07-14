import ast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import (Case, CharField, F, IntegerField, OuterRef,
                              Subquery)
from django.db.models import Value as V
from django.db.models import When
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView

from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.views.reports.administrative_areas_reports import \
    build_stations_centers_and_sub_cons_list
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale, get_deployed_site_url)
from tally_ho.libs.views import mixins


def get_overvoted_forms_queryset(tally_id, data=None):
    station_id_query = Subquery(
        Station.objects.filter(
            tally__id=tally_id,
            center__code=OuterRef("result_form__center__code"),
            station_number=OuterRef("result_form__station_number"),
        ).values("id")[:1],
        output_field=IntegerField(),
    )
    station_registrants_query = Subquery(
        Station.objects.filter(
            tally__id=tally_id, id=OuterRef("station_id_num")
        ).values("registrants")[:1],
        output_field=IntegerField(),
    )
    station_gender_query = Subquery(
        Station.objects.filter(
            tally__id=tally_id,
            center__code=OuterRef("result_form__center__code"),
            station_number=OuterRef("result_form__station_number"),
        ).values("gender")[:1],
        output_field=IntegerField(),
    )
    recon_forms = (
        ReconciliationForm.objects.filter(
            result_form__tally__id=tally_id,
            result_form__form_state=FormState.ARCHIVED,
            entry_version=EntryVersion.FINAL,
            active=True,
        )
        .annotate(
            barcode=F("result_form__barcode"), station_id_num=station_id_query
        )
        .values("barcode")
        .annotate(
            ballots_inside=F("number_of_voter_cards_in_the_ballot_box"),
            station_registrants=station_registrants_query,
            station_id=F("station_id_num"),
            station_gender_code=station_gender_query,
            station_gender=Case(
                When(station_gender_code=0, then=V("Man")),
                default=V("Woman"),
                output_field=CharField(),
            ),
            station_number=F("result_form__station_number"),
            center_code=F("result_form__center__code"),
            race=F("result_form__ballot__electrol_race__election_level"),
            sub_race=F("result_form__ballot__electrol_race__ballot_name"),
            municipality_name=F("result_form__center__sub_constituency__name"),
            municipality_code=F("result_form__center__sub_constituency__code"),
        )
    )

    if data:
        sub_con_codes = data.get("sub_con_codes") or []
        election_level_names = data.get("election_level_names") or []
        sub_race_type_names = data.get("sub_race_type_names") or []
        if sub_con_codes:
            recon_forms = recon_forms.filter(
                municipality_code__in=sub_con_codes
            )
        if election_level_names:
            recon_forms = recon_forms.filter(race__in=election_level_names)
        if sub_race_type_names:
            recon_forms = recon_forms.filter(sub_race__in=sub_race_type_names)
    forms = [
        recon_form
        for recon_form in recon_forms
        if recon_form.get("ballots_inside")
        > (recon_form.get("station_registrants") or 0)
    ]
    return forms


class OvervotedResultFormsDataView(
    LoginRequiredMixin,
    mixins.GroupRequiredMixin,
    mixins.TallyAccessMixin,
    BaseDatatableView,
):
    group_required = groups.TALLY_MANAGER
    columns = [
        "barcode",
        "center_code",
        "station_number",
        "ballots_inside",
        "station_registrants",
        "race",
        "sub_race",
        "municipality_name",
        "municipality_code",
    ]
    order_columns = columns

    def get_initial_queryset(self, data=None):
        tally_id = self.kwargs.get("tally_id")
        return get_overvoted_forms_queryset(tally_id, data)

    def get(self, request, *args, **kwargs):
        request_data = request.GET.get("data")
        data = None
        if request_data:
            try:
                data = ast.literal_eval(request_data)
            except Exception:
                data = None
        queryset = self.get_initial_queryset(data)
        total_records = len(queryset)
        page = request.GET.get("start", 0)
        page_size = request.GET.get("length", 10)
        search = request.GET.get("search[value]", None)

        # Filtering
        if search:
            queryset = [
                row for row in queryset if search.lower() in str(row).lower()
            ]
            total_records = len(queryset)

        # Paging
        if page_size == "-1":
            page_records = queryset
        else:
            page_records = queryset[int(page) : int(page) + int(page_size)]

        response_data = JsonResponse(
            {
                "draw": int(request.GET.get("draw", 0)),
                "recordsTotal": total_records,
                "recordsFiltered": total_records,
                "data": page_records,
            }
        )
        return response_data


class OvervotedResultFormsView(
    LoginRequiredMixin,
    mixins.GroupRequiredMixin,
    TemplateView,
):
    group_required = groups.TALLY_MANAGER
    template_name = "reports/overvoted_forms.html"

    def get(self, request, *args, **kwargs):
        language_de = get_datatables_language_de_from_locale(self.request)
        columns = (
            "barcode",
            "center_code",
            "station_number",
            "ballots_inside",
            "station_registrants",
            "race",
            "sub_race",
            "municipality_name",
            "municipality_code",
        )
        dt_columns = [{"data": column} for column in columns]
        tally_id = self.kwargs.get("tally_id")
        _, _, sub_cons = build_stations_centers_and_sub_cons_list(tally_id)
        electrol_races = ElectrolRace.objects.filter(tally__id=tally_id)
        context_data = {
            "tally_id": tally_id,
            "remote_url": reverse(
                "overvoted-forms-data",
                kwargs={"tally_id": kwargs.get("tally_id")},
            ),
            "sub_cons": sub_cons,
            "election_level_names": set(
                electrol_races.values_list("election_level", flat=True)
            ),
            "sub_race_type_names": set(
                electrol_races.values_list("ballot_name", flat=True)
            ),
            "dt_columns": dt_columns,
            "languageDE": language_de,
            "deployedSiteUrl": get_deployed_site_url(),
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
        }
        return self.render_to_response(self.get_context_data(**context_data))
