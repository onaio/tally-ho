import json

from django.test import RequestFactory

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.center import Center
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.apps.tally.views.reports import (
    election_statistics_report
)
from tally_ho.libs.tests.test_base import (
    create_electrol_race, create_result_form, create_station, \
    create_reconciliation_form, create_sub_constituency, create_tally, \
    create_region, create_constituency, create_office, create_result, \
    create_candidates, TestBase, create_ballot
)
from tally_ho.libs.tests.fixtures.electrol_race_data import (
    electrol_races
)


class TestElectionStatisticsReports(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally,
            **electrol_races[0]
        )
        ballot = create_ballot(self.tally, electrol_race=self.electrol_race)
        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc = create_sub_constituency(
            code=1, tally=self.tally, field_office='1', ballots=[ballot])
        center, _ = Center.objects.get_or_create(
            code='1',
            mahalla='1',
            name='1',
            office=office,
            region='1',
            village='1',
            active=True,
            tally=self.tally,
            sub_constituency=self.sc,
            center_type=CenterType.GENERAL,
            constituency=self.constituency)
        self.station = create_station(
            center=center, registrants=20, tally=self.tally)
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station.station_number,
            ballot=ballot)
        self.recon_form = create_reconciliation_form(
            result_form=self.result_form,
            user=self.user,
            number_ballots_inside_box=20,
            number_cancelled_ballots=0,
            number_spoiled_ballots=0,
            number_unstamped_ballots=0,
            number_unused_ballots=0,
            number_valid_votes=20,
            number_invalid_votes=0,
            number_ballots_received=20,
        )
        votes = 20
        create_candidates(self.result_form, votes=votes, user=self.user,
                          num_results=1, tally=self.tally)
        for result in self.result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(self.result_form, result.candidate, self.user, votes)

    def test_generate_election_statistics(self):
        """
        Test generate_election_statistics function
        """
        # Data
        election_stats = \
            election_statistics_report.generate_election_statistics(
                self.tally.id, 'Presidential')
        fields = [
            'ballot_number',
            'stations_expected',
            'stations_counted',
            'percentage_of_stations_counted',
            'registrants_in_stations_counted',
            'voters_in_counted_stations',
            'percentage_turnout_in_stations_counted'
        ]
        aggregate_keys = [
            'stations_expected',
            'stations_counted',
            'registrants_in_stations_counted',
            'voters_in_counted_stations',
        ]

        for stat in election_stats:
            for field in fields:
                self.assertIn(field, stat)
        total = election_stats.pop()
        self.assertEqual(total['ballot_number'], 'Total')
        aggregate = {}
        for stat in election_stats:
            for record, value in enumerate(stat):
                if record in aggregate_keys:
                    if record in aggregate:
                        aggregate[record] += value
                    else:
                        aggregate[record] = value

        for key, val in enumerate(aggregate):
            self.assertEqual(total[key], val)
        self.result_form.form_state = FormState.UNSUBMITTED
        self.result_form.save()
        election_stats = \
            election_statistics_report.generate_election_statistics(
                self.tally.id, 'Presidential')
        fields.remove('ballot_number')
        fields.remove('stations_expected')
        for stat in election_stats:
            for k, v in stat.items():
                if k in fields:
                    self.assertEqual(v, 0)

    def test_generate_overview_election_statistics(self):
        """
        Test generate_overview_election_statistics function
        """
        election_stats = \
            election_statistics_report.generate_overview_election_statistics(
                self.tally.id, 'Presidential')
        fields = [
            'male_voters_in_counted_stations',
            'female_voters_in_counted_stations',
            'unisex_voters_in_counted_stations',
            'voters_in_counted_stations',
            'male_total_registrants_in_counted_stations',
            'female_total_registrants_in_counted_stations',
            'unisex_total_registrants_in_counted_stations',
            'total_registrants_in_counted_stations',
            'percentage_of_stations_processed',
            'male_projected_turnout_percentage',
            'female_projected_turnout_percentage',
            'unisex_projected_turnout_percentage',
            'projected_turnout_percentage'
        ]
        for field in fields:
            self.assertIn(field, election_stats.keys())
        self.assertEqual(election_stats['forms_expected'], 1)
        self.assertEqual(election_stats['forms_counted'], 1)
        self.assertEqual(election_stats['stations_expected'], 1)
        self.result_form.form_state = FormState.UNSUBMITTED
        self.result_form.save()
        election_stats = \
            election_statistics_report.generate_overview_election_statistics(
                self.tally.id, 'Presidential')
        for k, v in election_stats.items():
            if k in fields:
                self.assertEqual(v, 0)

    def test_election_statistics_data_view(self):
        """
        Test ElectionStatisticsDataView
        """
        view = election_statistics_report.ElectionStatisticsDataView.as_view()
        request = self.factory.get(
            '/reports/internal/election-statistics-data')
        request.user = self.user
        response = view(
            request, tally_id=self.tally.id, election_level='Presidential')
        data = json.loads(response.content.decode())['data'][0]

        election_stats = \
            election_statistics_report.generate_election_statistics(
                self.tally.id, 'Presidential')
        self.assertDictEqual(election_stats[0], data)

    def test_election_statistics_report_view(self):
        """
        Test ElectionStatisticsReportView
        """
        view = election_statistics_report\
            .ElectionStatisticsReportView.as_view()
        request = self.factory.get(
            '/reports/internal/election-statistics-report')
        request.user = self.user
        response = view(
            request, tally_id=self.tally.id, election_level='Presidential')

        self.assertEqual(response.status_code, 200)
