import json

from django.test import RequestFactory

from tally_ho.apps.tally.views.data import sub_constituency_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_electrol_race,
    create_sub_constituency,
    create_tally,
)


class TestSubConstituencyListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        electrol_race = create_electrol_race(
            self.tally,
            **electrol_races[0]
        )
        ballot = create_ballot(self.tally, electrol_race=electrol_race)
        create_sub_constituency(
            code=1,
            field_office='1',
            ballots=[ballot],
            name="Sub Con A",
            tally=self.tally,
        )

    def test_sub_cons_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.SubConstituencyListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Sub Constituencies List")

    def test_sub_cons_list_data_view(self):
        """
        Test that sub cons list data view returns correct data
        """
        view = views.SubConstituencyListDataView.as_view()
        mock_json_data =\
            ['1', 'Sub Con A', 'Presidential', 'ballot_number_presidential', 1]
        request = self.factory.get('/sub-cons-list-data')
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(
            mock_json_data, json.loads(response.content.decode())['data'][0])
