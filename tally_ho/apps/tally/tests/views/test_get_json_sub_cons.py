import json
from datetime import datetime

from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone

from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_electrol_race,
    create_sub_constituency,
    create_tally,
)


class GetJSONSubConsTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.url = reverse('download-sub-cons-list')
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

    def test_get_sub_cons_success(self):
        mock_queryset = [
            {
                'code': 1,
                'name': 'Sub Con A',
                'election_level': 'Presidential',
                'sub_race': 'ballot_number_presidential',
                'ballot_number': 1
            }
        ]
        request_data = json.dumps({'tally_id': self.tally.id})
        response = self.client.get(self.url, {'data': request_data})
        self.assertIsInstance(response, JsonResponse)

        response_data = json.loads(response.content)
        expected_data = {
            'data': mock_queryset,
            'created_at': response_data['created_at'],
        }
        self.assertEqual(response_data['data'], expected_data['data'])

        created_at = datetime.strptime(
            response_data['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        created_at = timezone.make_aware(created_at)
        self.assertTrue(created_at <= timezone.now())
