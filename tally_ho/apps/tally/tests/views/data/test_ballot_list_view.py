import json

from django.test import RequestFactory

from tally_ho.apps.tally.views.constants import show_inactive_query_param
from tally_ho.apps.tally.views.data import ballot_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_electrol_race, create_tally)


class TestBallotListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_ballot_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.BallotListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Ballot List")
        self.assertContains(response, "New Ballot")

    def test_ballot_list_data_view(self):
        """
        Test that ballot list data view returns correct data
        """
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(
            tally,
            **electrol_races[0]
        )
        ballot = create_ballot(tally, electrol_race=electrol_race)
        view = views.BallotListDataView.as_view()
        request = self.factory.post('/ballot-list-data')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        action_link =\
            str(
             '<a '
            f'href="/super-administrator/edit-ballot/{tally.id}/{ballot.id}"'
            ' class="btn btn-default btn-small">Edit</a>'
        )
        mock_json_data =\
            [
                '1',
                'True',
                'Presidential',
                'ballot_number_presidential',
                ballot.modified_date.strftime('%a, %d %b %Y %H:%M:%S %Z'),
                str(ballot.available_for_release),
                action_link]
        self.assertEqual(
                    mock_json_data,
                    json.loads(response.content.decode())['data'][0])

    def test_show_inactive_parameter_default_behavior(self):
        """
        Test that by default (show_inactive not set),
        only active ballots are shown
        """
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(
            tally,
            **electrol_races[0]
        )

        # Create an active ballot
        create_ballot(
            tally, electrol_race=electrol_race, active=True, number=101
        )

        # Create an inactive ballot
        create_ballot(
            tally, electrol_race=electrol_race, active=False, number=102
        )

        view = views.BallotListDataView.as_view()

        # Test without show_inactive parameter (default behavior)
        request = self.factory.post('/ballot-list-data')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        data = json.loads(response.content.decode())['data']

        # Extract ballot numbers from response
        ballot_numbers = [row[0] for row in data]

        # Should only contain the active ballot
        self.assertEqual(len(data), 1)
        self.assertIn('101', ballot_numbers)
        self.assertNotIn('102', ballot_numbers)

    def test_show_inactive_parameter_false(self):
        """
        Test that when show_inactive=false explicitly,
        only active ballots are shown
        """
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(
            tally,
            **electrol_races[0]
        )

        # Create an active ballot
        create_ballot(
            tally, electrol_race=electrol_race, active=True, number=201
        )

        # Create an inactive ballot
        create_ballot(
            tally, electrol_race=electrol_race, active=False, number=202
        )

        view = views.BallotListDataView.as_view()

        # Test with show_inactive=false explicitly
        request = self.factory.post(
            f'/ballot-list-data?{show_inactive_query_param}=false'
        )
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        data = json.loads(response.content.decode())['data']

        # Extract ballot numbers from response
        ballot_numbers = [row[0] for row in data]

        # Should only contain the active ballot
        self.assertEqual(len(data), 1)
        self.assertIn('201', ballot_numbers)
        self.assertNotIn('202', ballot_numbers)

    def test_show_inactive_parameter_true(self):
        """
        Test that when show_inactive=true,
        both active and inactive ballots are shown
        """
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(
            tally,
            **electrol_races[0]
        )

        # Create an active ballot
        create_ballot(
            tally, electrol_race=electrol_race, active=True, number=301
        )

        # Create an inactive ballot
        create_ballot(
            tally, electrol_race=electrol_race, active=False, number=302
        )

        view = views.BallotListDataView.as_view()

        # Test with show_inactive=true
        request = self.factory.post(
            f'/ballot-list-data?{show_inactive_query_param}=true'
        )
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        data = json.loads(response.content.decode())['data']

        # Extract ballot numbers from response
        ballot_numbers = [row[0] for row in data]

        # Should contain both ballots
        self.assertEqual(len(data), 2)
        self.assertIn('301', ballot_numbers)
        self.assertIn('302', ballot_numbers)

    def test_show_inactive_case_insensitive(self):
        """
        Test that show_inactive parameter is case insensitive
        for 'true' value
        """
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(
            tally,
            **electrol_races[0]
        )

        # Create ballots
        create_ballot(
            tally, electrol_race=electrol_race, active=True, number=401
        )
        create_ballot(
            tally, electrol_race=electrol_race, active=False, number=402
        )

        view = views.BallotListDataView.as_view()

        # Test with different case variations
        for value in ['True', 'TRUE', 'TrUe']:
            request = self.factory.post(
                f'/ballot-list-data?{show_inactive_query_param}={value}'
            )
            request.user = self.user
            response = view(request, tally_id=tally.pk)
            data = json.loads(response.content.decode())['data']

            # Should contain both ballots for all 'true' variations
            self.assertEqual(len(data), 2, f"Failed for value: {value}")

        # Test that other values default to showing only active
        for value in ['false', 'False', '1', 'yes', 'invalid']:
            request = self.factory.post(
                f'/ballot-list-data?{show_inactive_query_param}={value}'
            )
            request.user = self.user
            response = view(request, tally_id=tally.pk)
            data = json.loads(response.content.decode())['data']

            # Should only contain active ballot
            self.assertEqual(len(data), 1, f"Failed for value: {value}")

    def test_search_with_active_filter(self):
        """
        Test that search filtering works correctly with active filter
        """
        tally = create_tally()
        tally.users.add(self.user)

        # Create electrol races with different election levels
        electrol_race1 = create_electrol_race(
            tally,
            **electrol_races[0]  # Presidential
        )
        electrol_race2 = create_electrol_race(
            tally,
            election_level="Senate",
            ballot_name="ballot_number_senate"
        )

        # Create active and inactive ballots for each race
        create_ballot(
            tally, electrol_race=electrol_race1, active=True, number=501
        )
        create_ballot(
            tally, electrol_race=electrol_race1, active=False, number=502
        )
        create_ballot(
            tally, electrol_race=electrol_race2, active=True, number=503
        )
        create_ballot(
            tally, electrol_race=electrol_race2, active=False, number=504
        )

        view = views.BallotListDataView.as_view()

        # Test search with default active filter (only active ballots)
        request = self.factory.post('/ballot-list-data')
        request.user = self.user
        request.POST = {'search[value]': 'Presidential'}
        response = view(request, tally_id=tally.pk)
        data = json.loads(response.content.decode())['data']

        # Should only find active Presidential ballot
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][0], '501')  # ballot number

        # Test search with show_inactive=true
        request = self.factory.post(
            f'/ballot-list-data?{show_inactive_query_param}=true'
        )
        request.user = self.user
        request.POST = {'search[value]': 'Presidential'}
        response = view(request, tally_id=tally.pk)
        data = json.loads(response.content.decode())['data']

        # Should find both Presidential ballots
        self.assertEqual(len(data), 2)
        ballot_numbers = [row[0] for row in data]
        self.assertIn('501', ballot_numbers)
        self.assertIn('502', ballot_numbers)

    def test_ballot_list_view_query_param_propagation(self):
        """
        Test that BallotListView correctly propagates query parameters
        to data view URL
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.BallotListView.as_view()

        # Test without show_inactive parameter
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        # Check that remote_url is in context
        self.assertIn('remote_url', response.context_data)
        remote_url = response.context_data['remote_url']

        # URL should not contain show_inactive parameter
        self.assertNotIn(show_inactive_query_param, remote_url)

        # Test with show_inactive=true
        request = self.factory.get(f'/?{show_inactive_query_param}=true')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        remote_url = response.context_data['remote_url']

        # URL should contain show_inactive=true
        self.assertIn(f'{show_inactive_query_param}=true', remote_url)

    def test_ballot_list_view_context_includes_show_inactive(self):
        """
        Test that BallotListView includes show_inactive in template context
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.BallotListView.as_view()

        # Test default value when parameter not provided
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertIn('show_inactive', response.context_data)
        self.assertEqual(response.context_data['show_inactive'], 'false')

        # Test when parameter is explicitly set to true
        request = self.factory.get(f'/?{show_inactive_query_param}=true')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.context_data['show_inactive'], 'true')

        # Test when parameter is explicitly set to false
        request = self.factory.get(f'/?{show_inactive_query_param}=false')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.context_data['show_inactive'], 'false')

    def test_ballot_list_view_checkbox_rendering(self):
        """
        Test that the template correctly renders the checkbox
        based on show_inactive
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.BallotListView.as_view()

        # Test checkbox is unchecked by default
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        # Checkbox should not be checked
        self.assertNotContains(response, 'id="show-inactive-ballots" checked')
        self.assertContains(response, 'id="show-inactive-ballots"')

        # Test checkbox is checked when show_inactive=true
        request = self.factory.get(f'/?{show_inactive_query_param}=true')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        # Checkbox should be checked
        self.assertContains(response, 'id="show-inactive-ballots" checked')

    def test_multiple_ballots_ordering(self):
        """
        Test that ballots are returned in correct order (by number)
        """
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(
            tally,
            **electrol_races[0]
        )

        # Create ballots in non-sequential order
        create_ballot(
            tally, electrol_race=electrol_race, active=True, number=603
        )
        create_ballot(
            tally, electrol_race=electrol_race, active=True, number=601
        )
        create_ballot(
            tally, electrol_race=electrol_race, active=True, number=602
        )

        view = views.BallotListDataView.as_view()
        request = self.factory.post('/ballot-list-data')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        data = json.loads(response.content.decode())['data']

        # Verify ballots are returned in order by number
        ballot_numbers = [row[0] for row in data]
        self.assertEqual(ballot_numbers, ['601', '602', '603'])
