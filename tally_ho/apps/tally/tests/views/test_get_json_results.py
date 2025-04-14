from datetime import datetime
from django.urls import reverse
from tally_ho.libs.tests.test_base import (
    TestBase, create_ballot, create_candidate, create_result,
    create_result_form, create_electrol_race, create_center,
    create_office, create_sub_constituency)
from django.http import JsonResponse
import json
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally
from django.utils import timezone
from tally_ho.libs.models.enums.form_state import FormState

class GetJSONResultsTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.url = reverse('download-results')

    def test_get_results_success(self):
        # Create electrol race
        electrol_race = create_electrol_race(
            self.tally,
            election_level='Level 1',
            ballot_name='Type A'
        )

        # Create ballot
        ballot = create_ballot(
            self.tally,
            electrol_race=electrol_race,
            available_for_release=True
        )

        # Create candidate
        candidate = create_candidate(
            ballot,
            'Candidate A',
            tally=self.tally
        )
        sub_constituency = create_sub_constituency(
            name='Sub Con A',
            tally=self.tally
        )

        center = create_center(
            code='1',
            tally=self.tally,
            sub_constituency=sub_constituency
        )

        office = create_office(
            name='Office A',
            tally=self.tally
        )

        # Create result form
        result_form = create_result_form(
            ballot=ballot,
            center=center,
            office=office,
            form_state=FormState.ARCHIVED,
            tally=self.tally
        )

        # Create result
        create_result(
            result_form,
            candidate,
            self.user,
            votes=100
        )

        request_data = json.dumps({'tally_id': self.tally.id})
        response = self.client.get(self.url, {'data': request_data})
        self.assertIsInstance(response, JsonResponse)

        response_data = json.loads(response.content)
        expected_data = {
            'data': [{
                'candidate__candidate_id': 1,
                'candidate__ballot__number': 1,
                'candidate__ballot__electrol_race__id': 1,
                'candidate__ballot__electrol_race__election_level': 'Level 1',
                'candidate__ballot__electrol_race__ballot_name': 'Type A',
                'candidate_number': 1,
                'candidate_name': 'Candidate A',
                'ballot_number': 1,
                'total_votes': 100,
                'order': 1,
                'candidate_status': 'enabled',
                'electrol_race_id': 1,
                'election_level': 'Level 1',
                'sub_race_type': 'Type A',
                'candidate_id': 1,
                'valid_votes': 100,
                'metadata': [{
                    'barcode': '123456789',
                    'gender': 'MALE',
                    'station_number': None,
                    'center_code': 1,
                    'center_name': '1',
                    'office_name': 'Office A',
                    'office_number': None,
                    'sub_con_name': 'Sub Con A',
                    'sub_con_code': 1
            }]}],
            'created_at': response_data['created_at'],
        }

        self.assertEqual(response_data['data'], expected_data['data'])

        created_at = datetime.strptime(
            response_data['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        created_at = timezone.make_aware(created_at)
        self.assertTrue(created_at <= timezone.now())
