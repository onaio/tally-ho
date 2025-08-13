import json

from django.test import RequestFactory

from tally_ho.apps.tally.views.data import ballot_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_electrol_race,
    create_tally,
)


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
