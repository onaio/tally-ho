from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Sum
from django.urls import reverse
from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models import (Constituency, Region, Result,
                                        ResultForm, Station, SubConstituency)
from tally_ho.apps.tally.models.office import Office
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.reports.list_base_data_view import NoneQsBaseDataView
from tally_ho.libs.views.mixins import (DataTablesMixin, GroupRequiredMixin,
                                        TallyAccessMixin)


def get_regions(tally_id):
    return (
        Region.objects.filter(tally_id=tally_id)
        .annotate(area_name=F("name"))
        .values("area_name", "id")
    )


def get_offices(tally_id):
    return (
        Office.objects.filter(tally_id=tally_id)
        .annotate(area_name=F("name"))
        .values("area_name", "id")
    )


def get_constituencies(tally_id):
    return (
        Constituency.objects.filter(tally_id=tally_id)
        .annotate(area_name=F("name"))
        .values("area_name", "id")
    )


def get_sub_constituencies(tally_id):
    return (
        SubConstituency.objects.filter(tally_id=tally_id)
        .annotate(area_name=F("code"))
        .values("area_name", "id")
    )


def get_stations_in_admin_area(tally_stations_qs, admin_level, admin_area):
    """
    get stations in a given administrative area across any of the
    4 supported admin levels.
    """
    area_filter_key = "center__region"
    if admin_level == "office":
        area_filter_key = "center__office"
    elif admin_level == "constituency":
        area_filter_key = "center__constituency"
    elif admin_level == "sub_constituency":
        area_filter_key = "center__sub_constituency"

    area_filter_map = {area_filter_key: admin_area}

    return tally_stations_qs.filter(active=True, **area_filter_map)


def get_result_forms_for_station_in_admin_area(
    tally_id, admin_level, admin_area, station_id, station_number
):
    """
    get distinct result forms for a given station
    """
    admin_area_name_filter = "center__region"
    if admin_level == "office":
        admin_area_name_filter = "center__office"
    elif admin_level == "constituency":
        admin_area_name_filter = "center__constituency"
    elif admin_level == "sub_constituency":
        admin_area_name_filter = "center__sub_constituency"

    area_filter_map = {admin_area_name_filter: admin_area}

    return (
        ResultForm.objects.filter(
            tally__id=tally_id,
            **area_filter_map,
            center__stations__id=station_id,
            station_number=station_number,
        )
        .values_list("form_state", flat=True)
        .distinct()
    )


def get_station_votes_in_admin_area(
    tally_id,
    admin_level,
    admin_area,
    station_id,
    station_number,
    station_races,
):
    """
    Gets the station votes grouped by races for the given station.
    """
    admin_area_name_filter = "center__region"
    if admin_level == "office":
        admin_area_name_filter = "center__office"
    elif admin_level == "constituency":
        admin_area_name_filter = "center__constituency"
    elif admin_level == "sub_constituency":
        admin_area_name_filter = "center__sub_constituency"

    area_filter_map = {f"result_form__{admin_area_name_filter}": admin_area}

    return (
        Result.objects.filter(
            result_form__tally__id=tally_id,
            **area_filter_map,
            result_form__center__stations__id=station_id,
            result_form__station_number=station_number,
            result_form__ballot__electrol_race_id__in=station_races,
            entry_version=EntryVersion.FINAL,
            active=True,
        )
        .annotate(
            race=F("result_form__ballot__electrol_race_id"),
            ballot_number=F("result_form__ballot__number"),
        )
        .values("race", "ballot_number")
        .annotate(race_voters=Sum("votes"))
        .order_by("-race_voters")
        .values("race_voters")
    )


class TurnoutReportByAdminAreasDataView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    NoneQsBaseDataView,
):
    group_required = groups.TALLY_MANAGER
    columns = (
        "area_code_or_name",
        "stations_expected",
        "stations_processed",
        "percentage_progress",
        "registrants_in_processed_stations",
        "voters_in_counted_stations",
        "percentage_turnout",
    )

    def get_initial_queryset(self):
        tally_id = self.kwargs.get("tally_id")
        admin_level = self.kwargs.get("admin_level")

        # get the full list of areas at the requested admin_level
        admin_areas_qs = get_regions(tally_id)
        if admin_level == "office":
            admin_areas_qs = get_offices(tally_id)
        elif admin_level == "constituency":
            admin_areas_qs = get_constituencies(tally_id)
        elif admin_level == "sub_constituency":
            admin_areas_qs = get_sub_constituencies(tally_id)

        ret_value = []

        tally_stations_qs = Station.objects.filter(tally_id=tally_id)
        stations_by_id = {station.id: station for station in tally_stations_qs}

        # Calculate voters in counted stations and turnout percentage
        for area in admin_areas_qs:
            response = {}
            area_code = area.get("id")
            if not admin_level or admin_level == "region":
                # regions are not linked by their ids, so we use name
                area_code = area.get("area_name")

            stations_in_area_qs = get_stations_in_admin_area(
                tally_stations_qs, admin_level, area_code
            )
            response["area_code_or_name"] = area.get("area_name")
            response["stations_expected"] = stations_in_area_qs.count()

            station_ids_by_race = (
                stations_in_area_qs.filter(
                    center__resultform__form_state=FormState.ARCHIVED,
                )
                .annotate(
                    race=F("center__resultform__ballot__electrol_race_id")
                )
                .values("id")
                .annotate(
                    races=ArrayAgg("race", distinct=True),
                )
            )
            voters = 0
            stations_processed = 0
            registrants_in_processed_stations = 0
            for station in station_ids_by_race:
                station_obj = stations_by_id.get(station.get("id"))
                if station_obj is None:
                    continue
                # Calculate stations processed and total registrants
                form_states = get_result_forms_for_station_in_admin_area(
                    tally_id,
                    admin_level,
                    area_code,
                    station_obj.pk,
                    station_obj.station_number,
                )

                if (
                    form_states.count() == 1
                    and form_states[0] == FormState.ARCHIVED
                ):
                    stations_processed += 1
                    registrants_in_processed_stations += (
                        station_obj.registrants
                    )

                    # Calculate voters voted in processed stations
                    votes = get_station_votes_in_admin_area(
                        tally_id,
                        admin_level,
                        area_code,
                        station_obj.pk,
                        station_obj.station_number,
                        station.get("races"),
                    )

                    if votes.count() != 0:
                        voters += votes[0].get("race_voters")

            # Calculate turnout percentage
            response["voters_in_counted_stations"] = voters
            response["stations_processed"] = stations_processed
            response["registrants_in_processed_stations"] = (
                registrants_in_processed_stations
            )
            if stations_processed == 0:
                response["percentage_progress"] = 0
                response["percentage_turnout"] = 0
                ret_value.append(response)
                continue

            response["percentage_progress"] = round(
                100 * stations_processed / response["stations_expected"], 2
            )
            response["percentage_turnout"] = round(
                100 * voters / registrants_in_processed_stations, 2
            )
            ret_value.append(response)
        return ret_value

    def render_column(self, row, column):
        if column in self.columns:
            col_value = row[column]
            return str(f'<td class="center">{col_value}</td>')
        else:
            return super(
                TurnoutReportByAdminAreasDataView, self
            ).render_column(row, column)

    def get_aggregate(self, data):
        aggregate = {}
        aggregate["area_code_or_name"] = "Total"
        aggregate["stations_expected"] = sum(
            entry["stations_expected"] for entry in data
        )
        aggregate["stations_processed"] = sum(
            entry["stations_processed"] for entry in data
        )
        aggregate["percentage_progress"] = (
            0
            if aggregate["stations_expected"] == 0
            else round(
                100
                * aggregate["stations_processed"]
                / aggregate["stations_expected"],
                2,
            )
        )
        aggregate["registrants_in_processed_stations"] = sum(
            entry["registrants_in_processed_stations"] for entry in data
        )
        aggregate["voters_in_counted_stations"] = sum(
            entry["voters_in_counted_stations"] for entry in data
        )
        aggregate["percentage_turnout"] = (
            0
            if aggregate["registrants_in_processed_stations"] == 0
            else round(
                100
                * aggregate["voters_in_counted_stations"]
                / aggregate["registrants_in_processed_stations"],
                2,
            )
        )
        return self.prepare_results([aggregate])


class TurnoutReportByAdminAreasView(
    LoginRequiredMixin, GroupRequiredMixin, DataTablesMixin, TemplateView
):
    group_required = groups.TALLY_MANAGER
    template_name = "reports/turnout_report_by_admin_area.html"

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        admin_level = kwargs.get("admin_level")

        context = {
            "tally_id": tally_id,
            "admin_level": admin_level,
            "remote_url": reverse("turnout-list-data", kwargs=kwargs),
            "regions_turnout_report_url": reverse(
                "turnout-list",
                kwargs={"tally_id": tally_id, "admin_level": "region"},
            ),
            "offices_remote_url": reverse(
                "turnout-list",
                kwargs={"tally_id": tally_id, "admin_level": "office"},
            ),
            "export_file_name": "turnout-report-by-admin-areas",
        }

        return self.render_to_response(self.get_context_data(**context))
