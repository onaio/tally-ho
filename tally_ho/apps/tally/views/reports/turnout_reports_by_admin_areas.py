from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from tally_ho.apps.tally.models import (
    Region, Constituency, SubConstituency,
    Station, ResultForm, Result
    )
from tally_ho.apps.tally.models.office import Office
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.utils.context_processors import \
    get_datatables_language_de_from_locale


def get_regions(tally_id):
    return Region.objects.filter(tally_id=tally_id).annotate(
        area_name=F("name")
        ).values('area_name')


def get_offices(tally_id):
    return Office.objects.filter(tally_id=tally_id).annotate(
        area_name=F("name")
        ).values("area_name")


def get_constituencies(tally_id):
    return Constituency.objects.filter(tally_id=tally_id).annotate(
        area_name=F("name")
        ).values("area_name")


def get_sub_constituencies(tally_id):
    return SubConstituency.objects.filter(tally_id=tally_id).annotate(
        area_name=F("code")
        ).values("area_name")


def get_stations_in_admin_area(tally_id, admin_level, admin_area):
    area_filter_key = "center__region"
    if admin_level == "office":
        area_filter_key = "center__office"
    elif admin_level == "constituency":
        area_filter_key = "center__constituency"
    elif admin_level == "sub_constituency":
        area_filter_key = "center__sub_constituency"

    area_filter_map = {area_filter_key: admin_area}

    return Station.objects.filter(tally_id=tally_id, **area_filter_map)


def get_result_forms_for_station_in_admin_area(
        tally_id, admin_level, admin_area, station
        ):
    admin_area_name_filter = "center__region"
    if admin_level == "office":
        admin_area_name_filter = "center__office__name"
    elif admin_level == "constituency":
        admin_area_name_filter = "center__constituency__name"
    elif admin_level == "sub_constituency":
        admin_area_name_filter = "center__sub_constituency__code"

    area_filter_map = {admin_area_name_filter: admin_area}

    return ResultForm.objects.filter(
        tally__id=tally_id,
        **area_filter_map,
        center__stations__id=station.get('id'),
        station_number=station.get('number'),
        ).values_list('form_state', flat=True).distinct()


def get_station_votes_in_admin_area(
        tally_id, admin_level, admin_area, station
        ):

    admin_area_name_filter = "center__region"
    if admin_level == "office":
        admin_area_name_filter = "center__office__name"
    elif admin_level == "constituency":
        admin_area_name_filter = "center__constituency__name"
    elif admin_level == "sub_constituency":
        admin_area_name_filter = "center__sub_constituency__code"

    area_filter_map = {f"result_form__{admin_area_name_filter}": admin_area}

    return Result.objects.filter(
        result_form__tally__id=tally_id,
        **area_filter_map,
        result_form__center__stations__id=station.get('id'),
        result_form__station_number=station.get('number'),
        result_form__ballot__race_type__in=station.get('races'),
        entry_version=EntryVersion.FINAL,
        active=True,
        ).annotate(
        race=F('result_form__ballot__race_type')
        ).values('race').annotate(
        race_voters=Sum('votes')
        ).order_by(
        '-race_voters'
        ).values(
        'race_voters'
        )


def turn_out_report_by_admin_levels_data(request, **kwargs):
    tally_id = kwargs.get('tally_id')
    admin_level = kwargs.get('admin_level')

    # TODO - dealing with unknown admin_levels as an edgecase.

    # get administrative areas # TODO - can search for the admin area here.
    admin_areas_qs = get_regions(tally_id)
    if admin_level == "office":
        admin_areas_qs = get_offices(tally_id)
    elif admin_level == "constituency":
        admin_areas_qs = get_constituencies(tally_id)
    elif admin_level == "sub_constituency":
        admin_areas_qs = get_sub_constituencies(tally_id)

    response = {}

    # Calculate voters in counted stations and turnout percentage
    for area in admin_areas_qs:
        area_name_or_code = area.get('name')
        stations_in_level_qs = get_stations_in_admin_area(
            tally_id, admin_level, area_name_or_code
            )
        response['stations_expected'] = stations_in_level_qs.count()

        station_ids_by_race = stations_in_level_qs.filter(
            center__resultform__form_state=FormState.ARCHIVED,
            ).annotate(
            race=F('center__resultform__ballot__race_type')
            ).values('id').annotate(
            races=ArrayAgg('race', distinct=True),
            number=F('station_number'),
            num_registrants=F('registrants')
            )
        voters = 0
        stations_processed = 0
        registrants_in_processed_stations = 0

        for station in station_ids_by_race:
            # Calculate stations processed and total registrants
            form_states = get_result_forms_for_station_in_admin_area(tally_id, admin_level, area_name_or_code, station)

            if form_states.count() == 1 and \
                    form_states[0] == FormState.ARCHIVED:
                stations_processed += 1
                registrants_in_processed_stations += \
                    station.get('num_registrants')

            # Calculate voters voted in processed stations
            votes = get_station_votes_in_admin_area(
                tally_id, admin_level, area_name_or_code, station
                )

            if votes.count() != 0:
                voters += votes[0].get('race_voters')

        # Calculate turnout percentage
        response['voters_in_counted_stations'] = voters
        response['stations_processed'] = stations_processed
        response['registrants_in_processed_stations'] = \
            registrants_in_processed_stations
        if stations_processed == 0:
            response['percentage_progress'] = 0
            response['percentage_turnout'] = 0
            continue

        response['percentage_progress'] = \
            round(
                100 * stations_processed / response['stations_expected'],
                2
                )
        response['percentage_turnout'] = \
            round(100 * voters / registrants_in_processed_stations, 2)

    # TODO - fix error
    # sorted_areas_by_turnout = \
    #     sorted(response, key=lambda x: -x['percentage_turnout'])
    sorted_areas_by_turnout = response
    return JsonResponse(
        {
            'data': sorted_areas_by_turnout,
            'draw': 1,
            'recordsFiltered': len(sorted_areas_by_turnout),
            'recordsTotal': len(sorted_areas_by_turnout),
            'results': 'ok'
            }
        )


def turn_out_report_by_admin_levels(request, **kwargs):
    tally_id = kwargs.get('tally_id')
    admin_level = kwargs.get('admin_level')
    language_de = get_datatables_language_de_from_locale(request)

    context = {
        'tally_id': tally_id,
        "admin_level": admin_level,
        'languageDE': language_de,
        "remote_url": reverse('turnout-list-data', kwargs=kwargs),
    }

    return render(
        request, 'reports/turnout_report_by_admin_area.html', context)
