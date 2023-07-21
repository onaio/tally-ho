import json
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.urls import reverse
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Sum, F
from guardian.mixins import LoginRequiredMixin
from tally_ho.apps.tally.models.ballot import Ballot

from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.utils.context_processors import\
    get_datatables_language_de_from_locale
from tally_ho.libs.utils.numbers import parse_int

from tally_ho.libs.views import mixins
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.station import Station


def generate_election_statistics(tally_id, election_level, gender=None):
    election_statistics = []
    # Calculate voters in counted stations
    election_level_ballots =\
        Ballot.objects.filter(
            tally_id=tally_id,
            electrol_race__election_level=election_level,).distinct()

    voters_in_counted_stations = 0
    stations_counted = 0
    registrants_in_stations_counted = 0

    aggregate_ballot_election_statistics = {
        'ballot_number': 'Total',
        'stations_expected': 0,
        'stations_counted': 0,
        'voters_in_counted_stations': 0,
        'registrants_in_stations_counted': 0,
    }

    for ballot in election_level_ballots:
        ballot_election_statistics = {
            'ballot_number': ballot.number,
            'stations_counted': 0,
            'percentage_of_stations_counted': 0,
            'voters_in_counted_stations': 0,
            'registrants_in_stations_counted': 0,
            'percentage_turnout_in_stations_counted': 0
        }
        # Calculate stations expected
        qs =\
            Station.objects.filter(
                tally_id=tally_id,
                center__resultform__ballot__electrol_race__election_level=\
                    election_level,
                center__resultform__ballot=ballot,)
        if gender:
            qs = qs.filter(gender=gender)

        ballot_election_statistics['stations_expected'] =\
            qs.distinct('station_number', 'center', 'tally').count()
        aggregate_ballot_election_statistics['stations_expected'] += \
            ballot_election_statistics['stations_expected']

        ballot_stations_with_archived_forms = qs.filter(
            center__resultform__form_state=FormState.ARCHIVED,
        ).distinct()
        # Calculate stations processed/counted per ballot and total registrants
        for station in ballot_stations_with_archived_forms:
            form_states =\
                ResultForm.objects.filter(
                    tally__id=tally_id,
                    center__resultform__ballot__electrol_race__election_level=\
                    election_level,
                    center__resultform__ballot=ballot,
                    center=station.center,
                    station_number=station.station_number,
                    ).values_list('form_state', flat=True).distinct()

            station_is_processed =\
                form_states.count() == 1 and\
                form_states[0] == FormState.ARCHIVED
            if station_is_processed is False:
                ballot_election_statistics['stations_counted'] = 0
                ballot_election_statistics[
                    'percentage_of_stations_counted'] = 0
                ballot_election_statistics['voters_in_counted_stations'] = 0
                ballot_election_statistics[
                    'registrants_in_stations_counted'] = 0
                ballot_election_statistics[
                    'percentage_turnout_in_stations_counted'] = 0
                continue

            stations_counted += 1
            if station.registrants:
                registrants_in_stations_counted += station.registrants

            # Calculate voters voted in processed stations
            votes =\
                Result.objects.filter(
                    result_form__tally__id=tally_id,
                    result_form__ballot__electrol_race__election_level=\
                        election_level,
                    result_form__ballot=ballot,
                    result_form__center=station.center,
                    result_form__station_number=station.station_number,
                    entry_version=EntryVersion.FINAL,
                    active=True,
                    ).annotate(
                        race=F(
                        'result_form__ballot__electrol_race__election_level')
                    ).values('race').annotate(
                        race_voters=Sum('votes')
                    ).order_by(
                        '-race_voters'
                    ).values(
                        'race_voters'
                    )
            if votes.count() != 0:
                voters_in_counted_stations += votes[0].get('race_voters')

        # Calculate turnout percentage
        if stations_counted != 0:
            ballot_election_statistics['stations_counted'] = stations_counted
            ballot_election_statistics[
                'percentage_of_stations_counted'] = round(
                    100 * stations_counted / ballot_election_statistics[
                        'stations_expected'],
                    2)
            ballot_election_statistics['voters_in_counted_stations'] =\
                voters_in_counted_stations
            ballot_election_statistics['registrants_in_stations_counted'] =\
                registrants_in_stations_counted
            ballot_election_statistics[
                'percentage_turnout_in_stations_counted'] =\
                round(
                    100 * voters_in_counted_stations /
                    registrants_in_stations_counted,
                    2) if registrants_in_stations_counted else 0
            aggregate_ballot_election_statistics['stations_counted'] += \
                ballot_election_statistics['stations_counted']
            aggregate_ballot_election_statistics[
                'voters_in_counted_stations'] += ballot_election_statistics[
                'voters_in_counted_stations']
            aggregate_ballot_election_statistics[
                'registrants_in_stations_counted'] += \
                ballot_election_statistics['registrants_in_stations_counted']

        aggregate_ballot_election_statistics[
            'percentage_of_stations_counted'] = round(
            100 * aggregate_ballot_election_statistics['stations_counted'] /
            aggregate_ballot_election_statistics[
                'stations_expected'],
            2) if aggregate_ballot_election_statistics[
                'stations_expected'] else 0.0
        aggregate_ballot_election_statistics[
            'percentage_turnout_in_stations_counted'] = round(
            100 * aggregate_ballot_election_statistics[
                'voters_in_counted_stations'] /
            aggregate_ballot_election_statistics[
                'registrants_in_stations_counted'],
            2) if aggregate_ballot_election_statistics[
            'registrants_in_stations_counted'] else 0.0

        election_statistics.append(ballot_election_statistics)
    election_statistics.append(aggregate_ballot_election_statistics)
    return election_statistics


def generate_overview_election_statistics(tally_id, election_level):
    election_statistics = {
        'male_voters_in_counted_stations': 0,
        'female_voters_in_counted_stations': 0,
        'voters_in_counted_stations': 0,
        'male_total_registrants_in_counted_stations': 0,
        'female_total_registrants_in_counted_stations': 0,
        'total_registrants_in_counted_stations': 0,
        'percentage_of_stations_processed': 0.0,
        'male_projected_turnout_percentage': 0.0,
        'female_projected_turnout_percentage': 0.0,
        'projected_turnout_percentage': 0.0
    }
    result_forms_expected = ResultForm.objects.filter(
                tally__id=tally_id,
                center__resultform__ballot__electrol_race__election_level=\
                election_level).distinct()
    forms_expected = result_forms_expected.count()
    election_statistics['forms_expected'] = forms_expected
    forms_counted =\
        result_forms_expected.filter(form_state=FormState.ARCHIVED).count()
    election_statistics['forms_counted'] = forms_counted
    election_statistics['completion_percentage'] =\
            round(100 * forms_counted / forms_expected, 2)
    # Calculate voters in counted stations
    qs =\
        Station.objects.filter(
            tally_id=tally_id,
            center__resultform__ballot__electrol_race__election_level=\
                election_level,
        )
    election_statistics['stations_expected'] =\
        qs.distinct('station_number', 'center', 'tally').count()

    station_ids_by_races = qs.filter(
        center__resultform__form_state=FormState.ARCHIVED,
    ).values('id').annotate(
        number=F('station_number'),
        station_gender=F('gender'),
        num_registrants=F('registrants')
    ).distinct()
    voters = 0
    male_voters = 0
    female_voters = 0
    stations_counted = 0
    total_male_registrants_in_counted_stations = 0
    total_female_registrants_in_counted_stations = 0
    total_registrants_in_counted_stations = 0
    for station in station_ids_by_races:
        # Calculate stations processed and total registrants
        form_states =\
            ResultForm.objects.filter(
                tally__id=tally_id,
                center__resultform__ballot__electrol_race__election_level=\
                election_level,
                center__stations__id=station.get('id'),
                station_number=station.get('number'),
                ).values_list('form_state', flat=True).distinct()

        station_is_processed =\
            form_states.count() == 1 and\
            form_states[0] == FormState.ARCHIVED
        if station_is_processed is False:
            election_statistics['male_voters_in_counted_stations'] = 0
            election_statistics['female_voters_in_counted_stations'] = 0
            election_statistics['voters_in_counted_stations'] = 0
            election_statistics[
                'male_total_registrants_in_counted_stations'] = 0
            election_statistics[
                'female_total_registrants_in_counted_stations'] = 0
            election_statistics['total_registrants_in_counted_stations'] = 0
            election_statistics['percentage_of_stations_processed'] = 0.0
            election_statistics['male_projected_turnout_percentage'] = 0.0
            election_statistics['female_projected_turnout_percentage'] = 0.0
            election_statistics['projected_turnout_percentage'] = 0.0
            continue

        stations_counted += 1
        total_registrants_in_counted_stations +=\
            station.get('num_registrants')
        if station.get('gender') == Gender.MALE:
                total_male_registrants_in_counted_stations +=\
                    station.get('num_registrants')
        elif station.get('gender') == Gender.FEMALE:
            total_female_registrants_in_counted_stations +=\
                station.get('num_registrants')

        # Calculate voters voted in processed stations
        votes =\
            Result.objects.filter(
                result_form__tally__id=tally_id,
                result_form__ballot__electrol_race__election_level=\
                    election_level,
                result_form__center__stations__id=station.get('id'),
                result_form__station_number=station.get('number'),
                entry_version=EntryVersion.FINAL,
                active=True,
                ).annotate(
                    race=F(
                    'result_form__ballot__electrol_race__election_level')
                ).values('race').annotate(
                    race_voters=Sum('votes')
                ).order_by(
                    '-race_voters'
                ).values(
                    'race_voters'
                )
        if votes.count() != 0:
            voters += votes[0].get('race_voters')
            if station.get('gender') == Gender.MALE:
                male_voters += votes[0].get('race_voters')
            elif station.get('gender') == Gender.FEMALE:
                female_voters += votes[0].get('race_voters')

    # Calculate turnout percentage
    if stations_counted != 0:
        election_statistics['voters_in_counted_stations'] = voters
        election_statistics['total_registrants_in_counted_stations'] =\
            total_registrants_in_counted_stations
        election_statistics['projected_turnout_percentage'] =\
            round(100 * voters / total_registrants_in_counted_stations, 2)
        # Male station statistics
        election_statistics['male_voters_in_counted_stations'] = male_voters
        election_statistics['male_total_registrants_in_counted_stations'] =\
            total_male_registrants_in_counted_stations
        election_statistics['male_projected_turnout_percentage'] =\
            round(100 *\
                  male_voters / total_male_registrants_in_counted_stations,
                  2)
        # Female station statistics
        election_statistics['female_voters_in_counted_stations'] =\
            female_voters
        election_statistics['female_total_registrants_in_counted_stations'] =\
            total_female_registrants_in_counted_stations
        election_statistics['female_projected_turnout_percentage'] =\
            round(100 *\
                  female_voters / total_female_registrants_in_counted_stations,
                  2)

    return election_statistics


class ElectionStatisticsDataView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 mixins.TallyAccessMixin,
                                 BaseDatatableView):
    group_required = groups.TALLY_MANAGER
    model = Station
    columns = ('ballot_number',
               'stations_expected',
               'stations_counted',
               'percentage_of_stations_counted',
               'registrants_in_stations_counted',
               'voters_in_counted_stations',
               'percentage_turnout_in_stations_counted')

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        election_level = kwargs.get('election_level')
        gender_value = None
        gender = []

        if request.POST.get('data'):
            data = json.loads(request.POST.get('data'))
            if data:
                gender_value =\
                    parse_int(data.get('gender_value'))
                gender =\
                    [gender for gender in Gender\
                        if gender.value == gender_value]

        election_statistics =\
            generate_election_statistics(tally_id,
                                         election_level,
                                         gender=gender[0] if gender else None)

        total_records = len(election_statistics)
        page = request.POST.get('start', 0)
        page_size = request.POST.get('length', 10)

        if page_size == '-1':
            page_records = election_statistics
        else:
            page_records =\
                election_statistics[int(page):int(page) + int(page_size)]

        response_data = JsonResponse({
            'draw': int(request.POST.get('draw', 0)),
            'recordsTotal': total_records,
            'recordsFiltered': total_records,
            'data': page_records,
        })

        return response_data


class ElectionStatisticsReportView(LoginRequiredMixin,
                                   mixins.GroupRequiredMixin,
                                   TemplateView):
    group_required = groups.TALLY_MANAGER
    model = Station
    template_name = 'reports/election_statistics_report.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        language_de = get_datatables_language_de_from_locale(request)
        election_level = kwargs.get('election_level')
        election_statistics_report =\
            generate_overview_election_statistics(tally_id, election_level)
        dt_columns =\
            [
                { "data": "ballot_number" },
                { "data": "stations_expected" },
                { "data": "stations_counted" },
                { "data": "percentage_of_stations_counted" },
                { "data": "registrants_in_stations_counted" },
                { "data": "voters_in_counted_stations" },
                { "data": "percentage_turnout_in_stations_counted" },
            ]

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('election-statistics-data', kwargs=kwargs),
            tally_id=tally_id,
            languageDE=language_de,
            election_statistics_report=election_statistics_report,
            genders=[gender for gender in Gender],
            election_level=election_level,
            dt_columns=dt_columns,
        ))
