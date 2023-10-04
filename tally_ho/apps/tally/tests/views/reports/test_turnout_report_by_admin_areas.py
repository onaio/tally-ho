import json

from django.test import RequestFactory
from bs4 import BeautifulSoup

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.center import Center
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.apps.tally.views.reports.turnout_reports_by_admin_areas import (
    TurnoutReportByAdminAreasDataView, TurnoutReportByAdminAreasView
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


class TestTurnoutInAdminAreasReport(TestBase):
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
        self.sc = \
            create_sub_constituency(
                code=1, field_office='1', ballots=[ballot],
                tally=self.tally
                )
        center, _ = Center.objects.get_or_create(
            code='1',
            mahalla='1',
            name='1',
            office=office,
            region=self.region.name,
            village='1',
            active=True,
            tally=self.tally,
            sub_constituency=self.sc,
            center_type=CenterType.GENERAL,
            constituency=self.constituency
            )
        self.station = create_station(
            center=center, registrants=20, tally=self.tally
            )
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station.station_number,
            ballot=ballot
            )
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
        votes = 2
        create_candidates(
            self.result_form, votes=votes, user=self.user,
            num_results=1, tally=self.tally
            )
        for result in self.result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(self.result_form, result.candidate, self.user, votes)

    # TODO - use django.test.client
    def test_turnout_in_region_view(self):
        request = RequestFactory().get(
            f'/data/turnout-list/{self.tally.pk}/region/'
            )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByAdminAreasView.as_view()
        response = view(request, tally_id=self.tally.pk)
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "xml")

        table_header_texts = [header.text for header in
                              doc.find('thead').findAll('th')]
        self.assertEqual(
            table_header_texts, ['Region',
                                 'Stations Expected',
                                 'Stations Counted',
                                 '% Progress',
                                 'Registrants in Counted Stations',
                                 'Votes Cast in Counted Stations',
                                 '% Turnout']
            )

    def test_turnout_in_office_view(self):
        request = RequestFactory().get(
            f'/data/turnout-list/{self.tally.pk}/office/'
            )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByAdminAreasView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level='office')
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "xml")

        table_header_texts = [header.text for header in
                              doc.find('thead').findAll('th')]
        self.assertEqual(
            table_header_texts, ['Office',
                                 'Stations Expected',
                                 'Stations Counted',
                                 '% Progress',
                                 'Registrants in Counted Stations',
                                 'Votes Cast in Counted Stations',
                                 '% Turnout']
            )

    def test_turnout_in_constituency_view(self):
        request = RequestFactory().get(
            f'/data/turnout-list/{self.tally.pk}/constituency/'
            )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByAdminAreasView.as_view()
        response = view(
            request, tally_id=self.tally.pk,
            admin_level='constituency'
            )
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "xml")

        table_header_texts = [header.text for header in
                              doc.find('thead').findAll('th')]
        self.assertEqual(
            table_header_texts, ['Main-Constituency',
                                 'Stations Expected',
                                 'Stations Counted',
                                 '% Progress',
                                 'Registrants in Counted Stations',
                                 'Votes Cast in Counted Stations',
                                 '% Turnout']
            )

    def test_turnout_in_sub_constituency_view(self):
        request = RequestFactory().get(
            f'/data/turnout-list/{self.tally.pk}/sub_constituency/'
            )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByAdminAreasView.as_view()
        response = view(
            request, tally_id=self.tally.pk,
            admin_level='sub_constituency'
            )
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "xml")

        table_header_texts = [header.text for header in
                              doc.find('thead').findAll('th')]
        self.assertEqual(
            table_header_texts, ['Sub constituency',
                                 'Stations Expected',
                                 'Stations Counted',
                                 '% Progress',
                                 'Registrants in Counted Stations',
                                 'Votes Cast in Counted Stations',
                                 '% Turnout']
            )

    def test_turnout_data_in_region_view(self):
        request = RequestFactory().get(
            f'/data/turnout-list-data/{self.tally.pk}/region/'
            )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByAdminAreasDataView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level='region')
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 200)

        (area_name, stations_expected, stations_processed,
         progress, registrants,
         voters,
         turnout) = content.get("data")[0]

        self.assertEqual(area_name, '<td class="center">Region</td>')
        self.assertEqual(stations_expected, '<td class="center">1</td>')
        self.assertEqual(stations_processed, '<td class="center">1</td>')
        self.assertEqual(progress, '<td class="center">100.0</td>')
        self.assertEqual(registrants, '<td class="center">20</td>')
        self.assertEqual(voters, '<td class="center">8</td>')
        self.assertEqual(turnout, '<td class="center">40.0</td>')

        (area_name, stations_expected, stations_processed,
         progress, registrants,
         voters,
         turnout) = content.get("aggregate")[0]

        self.assertEqual(area_name, '<td class="center">Total</td>')
        self.assertEqual(stations_expected, '<td class="center">1</td>')
        self.assertEqual(stations_processed, '<td class="center">1</td>')
        self.assertEqual(progress, '<td class="center">100.0</td>')
        self.assertEqual(registrants, '<td class="center">20</td>')
        self.assertEqual(voters, '<td class="center">8</td>')
        self.assertEqual(turnout, '<td class="center">40.0</td>')

    def test_turnout_data_in_office_view(self):
        request = RequestFactory().get(
            f'/data/turnout-list-data/{self.tally.pk}/office/'
            )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByAdminAreasDataView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level='office')
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 200)

        (area_name, stations_expected, stations_processed,
         progress, registrants,
         voters,
         turnout) = content.get("data")[0]

        self.assertEqual(area_name, '<td class="center">office</td>')
        self.assertEqual(stations_expected, '<td class="center">1</td>')
        self.assertEqual(stations_processed, '<td class="center">1</td>')
        self.assertEqual(progress, '<td class="center">100.0</td>')
        self.assertEqual(registrants, '<td class="center">20</td>')
        self.assertEqual(voters, '<td class="center">8</td>')
        self.assertEqual(turnout, '<td class="center">40.0</td>')

        (area_name, stations_expected, stations_processed,
         progress, registrants,
         voters,
         turnout) = content.get("aggregate")[0]

        self.assertEqual(area_name, '<td class="center">Total</td>')
        self.assertEqual(stations_expected, '<td class="center">1</td>')
        self.assertEqual(stations_processed, '<td class="center">1</td>')
        self.assertEqual(progress, '<td class="center">100.0</td>')
        self.assertEqual(registrants, '<td class="center">20</td>')
        self.assertEqual(voters, '<td class="center">8</td>')
        self.assertEqual(turnout, '<td class="center">40.0</td>')

    def test_turnout_data_in_sub_constituency_view(self):
        request = RequestFactory().get(
            f'/data/turnout-list-data/{self.tally.pk}/sub_constituency/'
            )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByAdminAreasDataView.as_view()
        response = view(
            request, tally_id=self.tally.pk,
            admin_level='sub_constituency'
            )
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 200)
        # import ipdb; ipdb.set_trace()

        (area_name, stations_expected, stations_processed,
         progress, registrants,
         voters,
         turnout) = content.get("data")[0]

        self.assertEqual(area_name, '<td class="center">1</td>')
        self.assertEqual(stations_expected, '<td class="center">1</td>')
        self.assertEqual(stations_processed, '<td class="center">1</td>')
        self.assertEqual(progress, '<td class="center">100.0</td>')
        self.assertEqual(registrants, '<td class="center">20</td>')
        self.assertEqual(voters, '<td class="center">8</td>')
        self.assertEqual(turnout, '<td class="center">40.0</td>')

        (area_name, stations_expected, stations_processed,
         progress, registrants,
         voters,
         turnout) = content.get("aggregate")[0]

        self.assertEqual(area_name, '<td class="center">Total</td>')
        self.assertEqual(stations_expected, '<td class="center">1</td>')
        self.assertEqual(stations_processed, '<td class="center">1</td>')
        self.assertEqual(progress, '<td class="center">100.0</td>')
        self.assertEqual(registrants, '<td class="center">20</td>')
        self.assertEqual(voters, '<td class="center">8</td>')
        self.assertEqual(turnout, '<td class="center">40.0</td>')
