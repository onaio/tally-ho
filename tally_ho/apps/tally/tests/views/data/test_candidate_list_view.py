import json
from django.test import RequestFactory

from tally_ho.apps.tally.views.data import candidate_list_view as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import\
    create_tally, create_office, create_ballot, create_result_form,\
    create_candidate, TestBase


class TestCandidateListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_candidate_list_view_get(self):
        """
        Test that candidate list view renders correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CandidateListView.as_view()
        request = self.factory.get('/candidate-list')
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Candidate List")

    def test_candidate_list_per_office_view_get(self):
        """
        Test that candidate list per office view renders correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        office = create_office(tally=tally)
        view = views.CandidateListView.as_view()
        request = self.factory.get('/candidate-list-per-office')
        request.user = self.user
        response = view(request, tally_id=tally.pk, office_id=office.id)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Candidate List Per Office")

    def test_candidate_list_data_view(self):
        """
        Test that candidate list data view returns correct data
        """
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=ballot)
        candidate = create_candidate(
            ballot=result_form.ballot,
            candidate_name='the candidate name',
            tally=tally)
        view = views.CandidateListDataView.as_view()
        request = self.factory.get('/candidate-list-data')
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        candidate_id, candidate_full_name, order, ballot_number,\
            race_type, modified_date_formatted, action_btn = json.loads(
                response.content.decode())['data'][0]

        self.assertEquals(candidate_id, candidate.id)
        self.assertEquals(candidate_full_name,
                          str(candidate.full_name))
        self.assertEquals(order, str(candidate.order))
        self.assertEquals(ballot_number, str(candidate.ballot.number))
        self.assertEquals(race_type, str(candidate.race_type.name))
        self.assertEquals(
            modified_date_formatted,
            candidate.modified_date.strftime('%a, %d %b %Y %H:%M:%S %Z'))
        self.assertEquals(
            action_btn,
            str('<a href="/super-administrator/candidate-disable'
                f'/{tally.id}/{candidate.id}" class="btn btn-default btn-small'
                '">Disable</a>'))

    def test_candidate_list_data_per_office_view(self):
        """
        Test that candidate list data per office view returns correct data
        """
        tally = create_tally()
        tally.users.add(self.user)
        office = create_office(tally=tally)
        ballot = create_ballot(tally=tally)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=ballot,
            office=office)
        candidate = create_candidate(
            ballot=result_form.ballot,
            candidate_name='the candidate name',
            tally=tally)
        view = views.CandidateListDataView.as_view()
        request = self.factory.get('/candidate-list-data-per-office')
        request.user = self.user
        response = view(request, tally_id=tally.pk, office_id=office.pk)

        candidate_id, candidate_full_name, order, ballot_number,\
            race_type, modified_date_formatted, action_btn = json.loads(
                response.content.decode())['data'][0]

        self.assertEquals(candidate_id, candidate.id)
        self.assertEquals(candidate_full_name,
                          str(candidate.full_name))
        self.assertEquals(order, str(candidate.order))
        self.assertEquals(ballot_number, str(candidate.ballot.number))
        self.assertEquals(race_type, str(candidate.race_type.name))
        self.assertEquals(
            modified_date_formatted,
            candidate.modified_date.strftime('%a, %d %b %Y %H:%M:%S %Z'))
        self.assertEquals(
            action_btn,
            str('<a href="/super-administrator/candidate-disable'
                f'/{tally.id}/{candidate.id}" class="btn btn-default btn-small'
                '">Disable</a>'))
