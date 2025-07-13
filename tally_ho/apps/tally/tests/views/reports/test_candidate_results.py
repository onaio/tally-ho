import json

from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.views.reports.candidate_results import (
    CandidateResultsDataView, CandidateResultsView)
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_candidate_result,
                                           create_constituency,
                                           create_electrol_race, create_office,
                                           create_reconciliation_form,
                                           create_region, create_result_form,
                                           create_station,
                                           create_sub_constituency,
                                           create_tally)


class TestCandidateResultsViews(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally,
            election_level='Municipal',
            ballot_name='Individual',
        )
        ballot = create_ballot(
            self.tally,
            electrol_race=self.electrol_race,
        )
        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc = create_sub_constituency(
            code=1,
            field_office='1',
            ballots=[ballot],
            tally=self.tally,
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
            constituency=self.constituency,
        )
        self.station = create_station(
            center=center,
            registrants=100,
            tally=self.tally,
            station_number=1,
            gender=Gender.MALE,
        )
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station.station_number,
            ballot=ballot,
        )
        self.recon_form = create_reconciliation_form(
            result_form=self.result_form,
            user=self.user,
            number_valid_votes=55,
            number_invalid_votes=5,
            number_ballots_received=100,
            entry_version=EntryVersion.FINAL,
        )
        create_candidate_result(
            self.result_form,
            votes=55,
            user=self.user,
            tally=self.tally,
        )

    def test_candidate_results_view_renders(self):
        """
        Test that the candidate results view renders successfully and uses
        the correct template. Also check for key context variables in the
        rendered HTML.
        """
        request = self.factory.get(
            reverse('candidate-results', kwargs={'tally_id': self.tally.pk})
        )
        request.user = self.user
        request.session = {}
        response = CandidateResultsView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)

        if hasattr(response, 'rendered_content'):
            content = response.rendered_content
        else:
            content = response.content.decode()
        doc = BeautifulSoup(content, "html.parser")

        table_headers = [th.text.strip() for th in doc.find_all('th')]
        expected_headers = [
            'Ballot', 'Race Number', 'Center', 'Station', 'Gender', 'Barcode',
            'Election Level', 'Sub Race Type', 'Voting District', 'Order',
            'Candidate Name', 'Candidate Id', 'Votes', 'Invalid Ballots',
            'Unstamped Ballots', 'Cancelled Ballots', 'Spoilt Ballots',
            'Unused Ballots', 'Number Of Voter Cards In The Ballot Box',
            'Received Ballots Papers', 'Valid Votes', 'Number Registrants',
            'Candidate Status',
        ]
        self.assertTrue(
            any(header in table_headers for header in expected_headers)
        )

        remote_url = reverse(
            'candidate-results-data', kwargs={'tally_id': self.tally.pk})
        self.assertIn(str(self.tally.pk), content)
        self.assertIn(remote_url, content)
        self.assertIn('deployedSiteUrl', content)

    def test_candidate_results_data_view_returns_data(self):
        """
        Test that the candidate results data endpoint returns expected data.
        """
        url = reverse(
            'candidate-results-data', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = self.user
        request.session = {}
        response = CandidateResultsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertIn('data', content)
        self.assertGreaterEqual(len(content['data']), 1)

        row = content['data'][0]
        expected_keys = [
            'ballot', 'race_number', 'center', 'station', 'gender', 'barcode',
            'election_level', 'sub_race_type', 'voting_district', 'order',
            'candidate_name', 'candidate_id', 'votes', 'invalid_ballots',
            'number_of_voter_cards_in_the_ballot_box',
            'received_ballots_papers', 'valid_votes', 'number_registrants',
            'candidate_status',
        ]
        for key in expected_keys:
            self.assertIn(key, row)

        self.assertEqual(row['votes'], 55)
        self.assertEqual(row['candidate_status'], 'enabled')

    def test_candidate_results_data_view_filtering(self):
        """
        Test filtering by search term in the data endpoint.
        """
        url = reverse(
            'candidate-results-data', kwargs={'tally_id': self.tally.pk}
        )

        request = self.factory.get(url, {'search[value]': 'candidate'})
        request.user = self.user
        request.session = {}
        response = CandidateResultsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())

        search_term = 'candidate'
        for row in content['data']:
            self.assertTrue(
                any(search_term in\
                    str(value).lower() for value in row.values())
            )

    def test_candidate_results_data_view_pagination(self):
        """
        Test pagination parameters in the data endpoint.
        """
        url = reverse(
            'candidate-results-data', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url, {'start': 0, 'length': 1})
        request.user = self.user
        request.session = {}
        response = CandidateResultsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)

        row = content['data'][0]
        self.assertEqual(row['votes'], 55)

    def test_candidate_results_view_requires_login(self):
        """
        Test that the candidate results view requires login.
        """
        url = reverse(
            'candidate-results', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = AnonymousUser()
        request.session = {}
        response = CandidateResultsView.as_view()(
            request, tally_id=self.tally.pk
        )

        self.assertIn(response.status_code, [302, 403])

    def test_candidate_results_data_view_empty(self):
        """
        Test the data endpoint with no candidate results.
        """
        self.result_form.reject(new_state=FormState.CLEARANCE)
        url = reverse(
            'candidate-results-data', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = self.user
        request.session = {}
        response = CandidateResultsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 0)
