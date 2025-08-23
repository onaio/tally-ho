import json

from django.test import RequestFactory

from tally_ho.apps.tally.views.data import candidate_list_view as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_candidate,
    create_office,
    create_result_form,
    create_tally,
)
from tally_ho.libs.utils.numbers import parse_int


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
        request = self.factory.get("/candidate-list")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate List")
        self.assertEqual(response.context_data["show_inactive"], "false")

    def test_candidate_list_per_office_view_get(self):
        """
        Test that candidate list per office view renders correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        office = create_office(tally=tally)
        view = views.CandidateListView.as_view()
        request = self.factory.get("/candidate-list-per-office")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk, office_id=office.id)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate List Per Office")
        self.assertEqual(response.context_data["show_inactive"], "false")

    def test_candidate_list_data_view(self):
        """
        Test that candidate list data view returns correct data
        """
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED, tally=tally, ballot=ballot
        )
        candidate = create_candidate(
            ballot=result_form.ballot,
            candidate_name="the candidate name",
            tally=tally,
        )
        view = views.CandidateListDataView.as_view()
        request = self.factory.get("/candidate-list-data")
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        (
            candidate_id,
            candidate_full_name,
            active,
            order,
            ballot_number,
            election_level,
            sub_race,
            modified_date_formatted,
            action_btn,
        ) = json.loads(response.content.decode())["data"][0]

        self.assertEqual(parse_int(candidate_id), candidate.candidate_id)
        self.assertEqual(candidate_full_name, candidate.full_name)
        self.assertEqual(active, str(candidate.active))
        self.assertEqual(parse_int(order), candidate.order)
        self.assertEqual(parse_int(ballot_number), candidate.ballot.number)
        self.assertEqual(
            election_level, candidate.ballot.electrol_race.election_level
        )
        self.assertEqual(sub_race, candidate.ballot.electrol_race.ballot_name)
        self.assertEqual(
            modified_date_formatted,
            candidate.modified_date.strftime("%a, %d %b %Y %H:%M:%S %Z"),
        )
        self.assertEqual(
            action_btn,
            str(
                '<a href="/super-administrator/candidate-disable'
                f'/{tally.id}/{candidate.id}" class="btn btn-default btn-small'
                '">Disable</a>'
            ),
        )

    def test_candidate_list_filters_inactive_ballots_by_default(self):
        """
        Test that inactive ballots are filtered out by default
        """
        tally = create_tally()
        tally.users.add(self.user)

        # Create active ballot with candidate
        active_ballot = create_ballot(tally=tally, active=True, number=10)
        active_candidate = create_candidate(
            ballot=active_ballot,
            candidate_name="active candidate",
            tally=tally,
        )

        # Create inactive ballot with candidate
        inactive_ballot = create_ballot(tally=tally, active=False, number=11)
        create_candidate(
            ballot=inactive_ballot,
            candidate_name="inactive candidate",
            tally=tally,
        )

        view = views.CandidateListDataView.as_view()
        request = self.factory.get("/candidate-list-data")
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        response_data = json.loads(response.content.decode())["data"]

        # Should only return active ballot candidate
        self.assertEqual(len(response_data), 1)
        returned_candidate_id = parse_int(response_data[0][0])
        self.assertEqual(returned_candidate_id, active_candidate.candidate_id)

    def test_candidate_list_shows_inactive_with_parameter(self):
        """
        Test that inactive ballots are shown when show_inactive=true
        """
        tally = create_tally()
        tally.users.add(self.user)

        # Create active ballot with candidate
        active_ballot = create_ballot(tally=tally, active=True, number=10)
        active_candidate = create_candidate(
            ballot=active_ballot,
            candidate_name="active candidate",
            tally=tally,
        )

        # Create inactive ballot with candidate
        inactive_ballot = create_ballot(tally=tally, active=False, number=11)
        inactive_candidate = create_candidate(
            ballot=inactive_ballot,
            candidate_name="inactive candidate",
            tally=tally,
        )

        view = views.CandidateListDataView.as_view()
        request = self.factory.get("/candidate-list-data?show_inactive=true")
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        response_data = json.loads(response.content.decode())["data"]

        # Should return both active and inactive ballot candidates
        self.assertEqual(len(response_data), 2)
        returned_candidate_ids = {parse_int(row[0]) for row in response_data}
        self.assertIn(active_candidate.candidate_id, returned_candidate_ids)
        self.assertIn(inactive_candidate.candidate_id, returned_candidate_ids)

    def test_get_candidates_list_filters_inactive_ballots(self):
        """
        Test the get_candidates_list function filters inactive ballots
        """
        tally = create_tally()

        # Create active ballot with candidate
        active_ballot = create_ballot(tally=tally, active=True, number=10)
        active_candidate = create_candidate(
            ballot=active_ballot,
            candidate_name="active candidate",
            tally=tally,
        )

        # Create inactive ballot with candidate
        inactive_ballot = create_ballot(tally=tally, active=False, number=11)
        inactive_candidate = create_candidate(
            ballot=inactive_ballot,
            candidate_name="inactive candidate",
            tally=tally,
        )

        # Test without show_inactive (should filter out inactive)
        request_data = json.dumps({"tally_id": tally.pk})
        request = self.factory.get(f"?data={request_data}")
        response = views.get_candidates_list(request)
        response_data = json.loads(response.content.decode())["data"]

        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["candidate_id"], active_candidate.candidate_id
        )

        # Test with show_inactive=true (should include both)
        request = self.factory.get(f"?data={request_data}&show_inactive=true")
        response = views.get_candidates_list(request)
        response_data = json.loads(response.content.decode())["data"]

        self.assertEqual(len(response_data), 2)
        returned_candidate_ids = {row["candidate_id"] for row in response_data}
        self.assertIn(active_candidate.candidate_id, returned_candidate_ids)
        self.assertIn(inactive_candidate.candidate_id, returned_candidate_ids)

    def test_candidate_list_per_office_with_inactive_filter(self):
        """
        Test per-office view respects active ballot filter
        """
        tally = create_tally()
        tally.users.add(self.user)
        office = create_office(tally=tally)

        # Create active ballot with candidate
        active_ballot = create_ballot(tally=tally, active=True, number=20)
        active_result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=active_ballot,
            office=office,
            barcode="111111111",
            serial_number=100,
        )
        active_candidate = create_candidate(
            ballot=active_result_form.ballot,
            candidate_name="active candidate",
            tally=tally,
        )

        # Create inactive ballot with candidate
        inactive_ballot = create_ballot(tally=tally, active=False, number=21)
        inactive_result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=inactive_ballot,
            office=office,
            barcode="222222222",
            serial_number=200,
        )
        inactive_candidate = create_candidate(
            ballot=inactive_result_form.ballot,
            candidate_name="inactive candidate",
            tally=tally,
        )

        view = views.CandidateListDataView.as_view()

        # Test without show_inactive (should filter out inactive)
        request = self.factory.get("/candidate-list-data-per-office")
        request.user = self.user
        response = view(request, tally_id=tally.pk, office_id=office.pk)
        response_data = json.loads(response.content.decode())["data"]

        self.assertEqual(len(response_data), 1)
        returned_candidate_id = parse_int(response_data[0][0])
        self.assertEqual(returned_candidate_id, active_candidate.candidate_id)

        # Test with show_inactive=true (should include both)
        request = self.factory.get(
            "/candidate-list-data-per-office?show_inactive=true"
        )
        request.user = self.user
        response = view(request, tally_id=tally.pk, office_id=office.pk)
        response_data = json.loads(response.content.decode())["data"]

        self.assertEqual(len(response_data), 2)
        returned_candidate_ids = {parse_int(row[0]) for row in response_data}
        self.assertIn(active_candidate.candidate_id, returned_candidate_ids)
        self.assertIn(inactive_candidate.candidate_id, returned_candidate_ids)

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
            office=office,
        )
        candidate = create_candidate(
            ballot=result_form.ballot,
            candidate_name="the candidate name",
            tally=tally,
        )
        view = views.CandidateListDataView.as_view()
        request = self.factory.get("/candidate-list-data-per-office")
        request.user = self.user
        response = view(request, tally_id=tally.pk, office_id=office.pk)
        (
            candidate_id,
            candidate_full_name,
            active,
            order,
            ballot_number,
            election_level,
            sub_race,
            modified_date_formatted,
            action_btn,
        ) = json.loads(response.content.decode())["data"][0]

        self.assertEqual(parse_int(candidate_id), candidate.candidate_id)
        self.assertEqual(candidate_full_name, candidate.full_name)
        self.assertEqual(active, str(candidate.active))
        self.assertEqual(parse_int(order), candidate.order)
        self.assertEqual(parse_int(ballot_number), candidate.ballot.number)
        self.assertEqual(
            election_level, candidate.ballot.electrol_race.election_level
        )
        self.assertEqual(sub_race, candidate.ballot.electrol_race.ballot_name)
        self.assertEqual(
            modified_date_formatted,
            candidate.modified_date.strftime("%a, %d %b %Y %H:%M:%S %Z"),
        )
        self.assertEqual(
            action_btn,
            str(
                '<a href="/super-administrator/candidate-disable'
                f'/{tally.id}/{candidate.id}" class="btn btn-default btn-small'
                '">Disable</a>'
            ),
        )
