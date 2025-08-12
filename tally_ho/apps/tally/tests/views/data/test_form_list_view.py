import datetime
import json

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from tally_ho.apps.tally.views.constants import (
    election_level_query_param,
    pending_at_state_query_param,
    sub_con_code_query_param,
    sub_race_query_param,
)
from tally_ho.apps.tally.views.data import form_list_view as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_center,
    create_electrol_race,
    create_result_form,
    create_result_forms_per_form_state,
    create_station,
    create_sub_constituency,
    create_tally,
)


class TestFormListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally,
            **electrol_races[0]
        )

    def test_access_control(self):
        view = views.FormListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)

        request.user = AnonymousUser()
        request.session = {}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)

    def test_form_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Form List")
        self.assertContains(response, "New Form")

    def test_csv_export(self):
        ballot = create_ballot(self.tally, self.electrol_race)
        sub_con = create_sub_constituency(code=12345,tally=self.tally)
        center_code = '12345'
        center = create_center(
            center_code, tally=self.tally, sub_constituency=sub_con)
        station = create_station(center)
        state = 'unsubmitted'
        form_state = FormState[state.upper()]
        barcode = f"{center_code}0{station.station_number}011"
        result_form = create_result_form(
                ballot=ballot,
                barcode=barcode,
                form_state=form_state,
                center=center,
                station_number=station.station_number,
                tally=self.tally
            )
        view = views.FormListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk, state=state)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = b"".join(response.streaming_content).decode('utf-8')
        self.assertIn(result_form.barcode, content)
        formatted_datestring = datetime.date.today().strftime("%Y%m%d")
        filename = f'{state}_form_list_{formatted_datestring}.csv'
        self.assertIn(filename, response.headers['Content-Disposition'])

    def test_form_not_received_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Forms Not Received")
        self.assertNotContains(response, "New Form")

    def test_form_not_received_list_csv_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, format='csv', tally_id=tally.pk)
        self.assertContains(response, "barcode")

    def test_forms_for_race(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        view = views.FormsForRaceView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, ballot=ballot.number, tally_id=tally.pk)
        self.assertContains(response, "Forms for Race %s" % ballot.number)
        self.assertNotContains(response, "New Form")

    def test_form_list_view_filter_on_query_params(self):
        """
        #369 - check that filter search params are passed on
        to data view. and data view uses the query params to
        filter
        """
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        view = views.FormListView.as_view()
        data_view = views.FormListDataView.as_view()
        request = self.factory.get(
            f'/1/?{pending_at_state_query_param}=data_entry_1'
            f'&{election_level_query_param}=HoR'
            f'&{sub_race_query_param}=ballot_number_HOR_women'
            f'&{sub_con_code_query_param}=12345'
            )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)
        raw_data_response_for_electrol_race_hor = data_view(
            request, tally_id=self.tally.pk
            ).content

        self.assertEqual(
            response.context_data['remote_url'],
            f"/data/form-list-data/{self.tally.pk}/?"
            "pending_at_form_state=data_entry_1"
            f'&{election_level_query_param}=HoR'
            f'&{sub_race_query_param}=ballot_number_HOR_women'
            "&sub_con_code=12345"
            )
        self.assertListEqual(response.template_name, ['data/forms.html'])

        data_response_for_electrol_race_hor = json.loads(
            raw_data_response_for_electrol_race_hor
            ).get('data')
        self.assertListEqual(data_response_for_electrol_race_hor, [])

        request = self.factory.get(
            f'/1/?{pending_at_state_query_param}='
            f'data_entry_1'
            f'&{election_level_query_param}='
            f'{self.electrol_race.election_level}'
            f'&{sub_race_query_param}={self.electrol_race.ballot_name}'
            f'&{sub_con_code_query_param}=12345'
            )
        request.user = self.user
        request.session = {}

        raw_data_response_for_electrol_race_presidential = data_view(
            request, tally_id=self.tally.pk
            ).content
        data_response_for_electrol_race_presidential = json.loads(
            raw_data_response_for_electrol_race_presidential
            ).get('data')
        self.assertEqual(len(data_response_for_electrol_race_presidential), 4)
        election_levels_in_response = [form[9] for form in
                                  data_response_for_electrol_race_presidential]
        sub_races_in_response = [form[10] for form in
                                  data_response_for_electrol_race_presidential]
        form_states_in_response = [form[12] for form in
                                   data_response_for_electrol_race_presidential]

        self.assertListEqual(
            election_levels_in_response,
            ['Presidential', 'Presidential', 'Presidential', 'Presidential']
            )
        self.assertListEqual(
            sub_races_in_response,
            [
                'ballot_number_presidential',
                'ballot_number_presidential',
                'ballot_number_presidential',
                'ballot_number_presidential'
            ]
            )
        expected_form_states = ['Audit', 'Clearance', 'Intake', 'Unsubmitted']
        for state in expected_form_states:
            self.assertIn(state, form_states_in_response)
