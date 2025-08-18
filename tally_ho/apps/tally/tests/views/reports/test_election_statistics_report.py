import json

from django.test import RequestFactory

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.views.reports import election_statistics_report
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_candidates,
                                           create_constituency,
                                           create_electrol_race, create_office,
                                           create_reconciliation_form,
                                           create_region, create_result,
                                           create_result_form, create_station,
                                           create_sub_constituency,
                                           create_tally)


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
        self.ballot = create_ballot(
            self.tally, electrol_race=self.electrol_race)
        self.region = create_region(tally=self.tally)
        self.office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc = create_sub_constituency(
            code=1, tally=self.tally, field_office='1', ballots=[self.ballot])
        self.center, _ = Center.objects.get_or_create(
            code='1',
            mahalla='1',
            name='1',
            office=self.office,
            region='1',
            village='1',
            active=True,
            tally=self.tally,
            sub_constituency=self.sc,
            center_type=CenterType.GENERAL,
            constituency=self.constituency)
        self.station = create_station(
            center=self.center, registrants=20, tally=self.tally)
        self.male_station = create_station(
            center=self.center, registrants=15, gender=Gender.MALE,
            station_number='002', tally=self.tally)
        self.female_station = create_station(
            center=self.center, registrants=25, gender=Gender.FEMALE,
            station_number='003', tally=self.tally)
        self.unisex_station = create_station(
            center=self.center, registrants=30, gender=Gender.UNISEX,
            station_number='004', tally=self.tally)
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=self.office,
            center=self.center,
            station_number=self.station.station_number,
            ballot=self.ballot)
        self.recon_form = create_reconciliation_form(
            result_form=self.result_form,
            user=self.user,
            number_valid_votes=20,
            number_invalid_votes=0,
            number_of_voters=20,
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

        for stat in election_stats:
            for field in fields:
                self.assertIn(field, stat)

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
        self.assertEqual(election_stats['stations_expected'], 4)
        # Test that unisex and female statistics are both zero initially
        # (since we only have result forms for the main station)
        self.assertEqual(
            election_stats['unisex_voters_in_counted_stations'], 0
        )
        self.assertEqual(
            election_stats['female_voters_in_counted_stations'], 0
        )
        create_result_form(
            barcode='012345678',
            tally=self.tally,
            form_state=FormState.UNSUBMITTED,
            office=self.office,
            center=self.center,
            station_number=self.station.station_number,
            ballot=self.ballot,
            serial_number=1,
            name='Another Result Form'
        )
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

    def test_election_statistics_data_view_with_gender_filter(self):
        """
        Test ElectionStatisticsDataView with gender filter
        """
        view = election_statistics_report.ElectionStatisticsDataView.as_view()
        request = self.factory.post(
            '/reports/internal/election-statistics-data',
            data={'data': json.dumps({'gender_value': Gender.MALE.value})})
        request.user = self.user
        response = view(
            request, tally_id=self.tally.id, election_level='Presidential')
        data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertIn('data', data)

    def test_generate_overview_election_statistics_with_mixed_genders(self):
        """
        Test overview election statistics with different gender stations
        """
        # Create result forms for additional stations
        male_result_form = create_result_form(
            barcode='012345679',
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=self.office,
            center=self.center,
            station_number=self.male_station.station_number,
            ballot=self.ballot,
            serial_number=2
        )
        unisex_result_form = create_result_form(
            barcode='012345680',
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=self.office,
            center=self.center,
            station_number=self.unisex_station.station_number,
            ballot=self.ballot,
            serial_number=3
        )

        # Create results for male station
        create_candidates(male_result_form, votes=10, user=self.user,
                          num_results=1, tally=self.tally)
        for result in male_result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()

        # Create results for unisex station
        create_candidates(unisex_result_form, votes=15, user=self.user,
                          num_results=1, tally=self.tally)
        for result in unisex_result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()

        election_stats = \
            election_statistics_report.generate_overview_election_statistics(
                self.tally.id, 'Presidential')

        # Verify that unisex values are not equal to female values
        self.assertNotEqual(
            election_stats['unisex_voters_in_counted_stations'],
            election_stats['female_voters_in_counted_stations']
        )
        self.assertNotEqual(
            election_stats['unisex_total_registrants_in_counted_stations'],
            election_stats['female_total_registrants_in_counted_stations']
        )

        # Verify that male statistics are properly calculated
        self.assertGreater(
            election_stats['male_voters_in_counted_stations'], 0
        )
        self.assertGreater(
            election_stats['male_total_registrants_in_counted_stations'], 0
        )

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

    def test_generate_election_statistics_with_no_archived_forms(self):
        """
        Test election statistics when no forms are archived
        """
        # Change result form state to unsubmitted
        self.result_form.form_state = FormState.UNSUBMITTED
        self.result_form.save()

        election_stats = \
            election_statistics_report.generate_election_statistics(
                self.tally.id, 'Presidential')

        # Should return statistics with zero counts
        for stat in election_stats:
            self.assertEqual(stat['stations_counted'], 0)
            self.assertEqual(stat['voters_in_counted_stations'], 0)

    def test_generate_election_statistics_excludes_inactive_ballots(self):
        """
        Test that election statistics only include data from active ballots
        """
        # Create an inactive ballot with its own result form
        inactive_electrol_race = create_electrol_race(
            self.tally,
            **electrol_races[1]
        )
        inactive_ballot = create_ballot(
            self.tally, electrol_race=inactive_electrol_race, active=False)

        # Create a new station for the inactive ballot
        inactive_station = create_station(
            center=self.center, registrants=30,
            station_number='005', tally=self.tally)

        # Create result form for inactive ballot
        inactive_result_form = create_result_form(
            barcode='987654321',
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=self.office,
            center=self.center,
            station_number=inactive_station.station_number,
            ballot=inactive_ballot,
            serial_number=99
        )

        # Add votes to inactive ballot result form
        votes = 15
        create_candidates(inactive_result_form, votes=votes, user=self.user,
                          num_results=1, tally=self.tally)
        for result in inactive_result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()

        # Generate election statistics - should only include active ballot
        election_stats = \
            election_statistics_report.generate_election_statistics(
                self.tally.id, 'Presidential')

        # Should have only one ballot (the active one)
        self.assertEqual(len(election_stats), 1)

        # Statistics should only reflect the active ballot
        stat = election_stats[0]
        self.assertEqual(stat['ballot_number'], self.ballot.number)
        self.assertEqual(stat['stations_counted'], 1)
        # 4 results * 20 votes each
        self.assertEqual(stat['voters_in_counted_stations'], 80)

    def test_generate_overview_election_statistics_excludes_inactive_ballots(
        self
    ):
        """
        Test overview election statistics exclude data from inactive ballots
        """
        # Create an inactive ballot with its own result form
        inactive_electrol_race = create_electrol_race(
            self.tally,
            **electrol_races[1]
        )
        inactive_ballot = create_ballot(
            self.tally, electrol_race=inactive_electrol_race, active=False)

        # Create a new station for the inactive ballot
        inactive_station = create_station(
            center=self.center, registrants=30,
            station_number='006', tally=self.tally)

        # Create result form for inactive ballot
        inactive_result_form = create_result_form(
            barcode='987654322',
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=self.office,
            center=self.center,
            station_number=inactive_station.station_number,
            ballot=inactive_ballot,
            serial_number=100
        )

        # Add votes to inactive ballot result form
        votes = 25
        create_candidates(inactive_result_form, votes=votes, user=self.user,
                          num_results=1, tally=self.tally)
        for result in inactive_result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()

        # Generate overview election statistics
        election_stats = \
            election_statistics_report.generate_overview_election_statistics(
                self.tally.id, 'Presidential')

        # Should only count the active ballot's form
        self.assertEqual(election_stats['forms_expected'], 1)
        self.assertEqual(election_stats['forms_counted'], 1)

        # Should only count stations with active ballots
        # (5 original stations including the new one)
        self.assertEqual(election_stats['stations_expected'], 5)

        # Should only include voters from active ballot
        self.assertEqual(election_stats['voters_in_counted_stations'], 80)
