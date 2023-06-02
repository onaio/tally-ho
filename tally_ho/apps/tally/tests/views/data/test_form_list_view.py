import json
from django.test import RequestFactory

from tally_ho.apps.tally.views.constants import (
    race_type_query_param,
    pending_at_state_query_param
    )
from tally_ho.apps.tally.views.data import form_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    create_ballot,
    create_tally,
    TestBase,
    issue_369_result_forms_data_setup,
    )


class TestFormListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

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
        tally = issue_369_result_forms_data_setup(self.user)

        view = views.FormListView.as_view()
        data_view = views.FormListDataView.as_view()
        request = self.factory.get(
            f'/1/?{pending_at_state_query_param}=data_entry_1'
            f'&{race_type_query_param}=presidential'
            )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=tally.pk)
        raw_data_response_for_president = data_view(
            request, tally_id=tally.pk
            ).content

        self.assertEqual(
            response.context_data['remote_url'],
            f"/data/form-list-data/{tally.pk}/?"
            "pending_at_form_state=data_entry_1&race_type=presidential"
            )
        self.assertListEqual(response.template_name, ['data/forms.html'])

        data_response_for_president = json.loads(
            raw_data_response_for_president
            ).get('data')
        self.assertListEqual(data_response_for_president, [])

        request = self.factory.get(
            f'/1/?{pending_at_state_query_param}='
            f'data_entry_1&{race_type_query_param}=general'
            )
        request.user = self.user
        request.session = {}

        raw_data_response_for_general = data_view(
            request, tally_id=tally.pk
            ).content
        data_response_for_general = json.loads(
            raw_data_response_for_general
            ).get('data')
        self.assertEqual(len(data_response_for_general), 4)
        race_types_in_response = [form[8] for form in
                                  data_response_for_general]
        form_states_in_response = [form[9] for form in
                                   data_response_for_general]

        self.assertListEqual(
            race_types_in_response,
            ['GENERAL', 'GENERAL', 'GENERAL', 'GENERAL']
            )
        self.assertListEqual(
            form_states_in_response,
            ['Audit', 'Clearance', 'Intake', 'Unsubmitted']
            )
