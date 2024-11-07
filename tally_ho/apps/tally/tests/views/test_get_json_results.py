from datetime import datetime
from django.urls import reverse
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.tests.test_base import TestBase
from django.http import JsonResponse
from unittest.mock import patch
import json
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally
from django.utils import timezone

class GetJSONResultsTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.url = reverse('download-results')

    @patch('tally_ho.apps.tally.views.reports.administrative_areas_reports.'
           'results_queryset')
    @patch('tally_ho.apps.tally.views.reports.administrative_areas_reports.'
           'get_total_valid_votes_per_electrol_race')
    def test_get_results_success(
        self,
        mock_get_total_valid_votes_per_electrol_race,
        mock_results_queryset):
        mock_results_queryset.return_value = [
            {
                'candidate_number': 1,
                'candidate_name': 'Candidate A',
                'total_votes': 100,
                'gender': Gender.MALE,
                'election_level': 'Level 1',
                'sub_race_type': 'Type A',
                'order': 1,
                'ballot_number': '1234',
                'candidate_status': 'active',
                'center_code': 'C1',
                'center_name': 'Center A',
                'office_number': 'O1',
                'office_name': 'Office A',
                'station_number': 'S1',
                'sub_con_code': 'SUB1',
                'electrol_race_id': 1,
                'sub_con_name': 'Sub Con A',
            }
        ]
        mock_get_total_valid_votes_per_electrol_race.return_value = 100

        request_data = json.dumps({'tally_id': self.tally.id})
        response = self.client.get(self.url, {'data': request_data})
        self.assertIsInstance(response, JsonResponse)

        response_data = json.loads(response.content)
        expected_data = {
            'data': [{
                'candidate_id': 1,
                'candidate_name': 'Candidate A',
                'total_votes': 100,
                'gender': Gender.MALE.name,
                'election_level': 'Level 1',
                'sub_race_type': 'Type A',
                'order': 1,
                'ballot_number': '1234',
                'candidate_status': 'active',
                'center_code': 'C1',
                'center_name': 'Center A',
                'office_number': 'O1',
                'office_name': 'Office A',
                'station_number': 'S1',
                'sub_con_code': 'SUB1',
                'valid_votes': 100,
                'sub_con_name': 'Sub Con A',
            }],
            'created_at': response_data['created_at'],
        }

        self.assertEqual(response_data['data'], expected_data['data'])

        created_at = datetime.strptime(
            response_data['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        created_at = timezone.make_aware(created_at)
        self.assertTrue(created_at <= timezone.now())
