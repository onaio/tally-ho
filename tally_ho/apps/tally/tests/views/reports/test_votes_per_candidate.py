import json
from django.test import RequestFactory

from tally_ho.apps.tally.views.reports import votes_per_candidate as views
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result import Result
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import\
    create_tally, create_result_form, create_center, create_station,\
    create_ballot, create_candidates, TestBase


class TestVotesPerCandidateListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

        self.tally = create_tally()
        self.tally.users.add(self.user)

        ballot = create_ballot(tally=self.tally)
        self.center = create_center('12345', tally=self.tally)
        self.station = create_station(self.center)
        result_form = create_result_form(
            tally=self.tally,
            ballot=ballot,
            center=self.center,
            station_number=self.station.station_number)
        votes = 12
        create_candidates(result_form, votes=votes, user=self.user,
                          num_results=1)

    def test_station_votes_per_candidate_list_view(self):
        """
        Test that Station votes per candidate list view renders correctly
        """
        view = views.VotesPerCandidateListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request,
                        tally_id=self.tally.pk,
                        station_number=self.station.station_number)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Station Votes per Candidate")
        self.assertContains(response, "Candidate Name")
        self.assertContains(response, "Votes")

    def test_center_votes_per_candidate_list_view(self):
        """
        Test that Center votes per candidate list view renders correctly
        """
        view = views.VotesPerCandidateListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request,
                        tally_id=self.tally.pk,
                        center_code=self.center.code)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Center Votes per Candidate")
        self.assertContains(response, "Candidate Name")
        self.assertContains(response, "Votes")

    def test_station_votes_per_candidate_list_data_view(self):
        """
        Test that Station votes per candidate list data view returns
        correct data
        """
        view = views.VotesPerCandidateListDataView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request,
                        tally_id=self.tally.pk,
                        station_number=self.station.station_number)

        candidates = Candidate.objects.all()
        first_candidate = candidates.first()
        first_candidate_votes = Result.objects.get(
            candidate=first_candidate).votes
        candidate_name, candidate_votes = json.loads(
            response.content.decode())['data'][0]

        self.assertEquals(
            candidate_name,
            str('<td class="center sorting_1">'
                f'{first_candidate.full_name}</td>'))
        self.assertEquals(
            candidate_votes,
            str('<td class="center">'
                f'{first_candidate_votes}</td>'))

    def test_center_votes_per_candidate_list_data_view(self):
        """
        Test that Center votes per candidate list data view returns
        correct data
        """
        view = views.VotesPerCandidateListDataView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request,
                        tally_id=self.tally.pk,
                        center_code=self.center.code)

        candidates = Candidate.objects.all()
        first_candidate = candidates.first()
        first_candidate_votes = Result.objects.get(
            candidate=first_candidate).votes
        candidate_name, candidate_votes = json.loads(
            response.content.decode())['data'][0]

        self.assertEquals(
            candidate_name,
            str('<td class="center sorting_1">'
                f'{first_candidate.full_name}</td>'))
        self.assertEquals(
            candidate_votes,
            str('<td class="center">'
                f'{first_candidate_votes}</td>'))
