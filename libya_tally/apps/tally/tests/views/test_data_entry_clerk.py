from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import data_entry_clerk as views
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_result_form,\
    create_candidate, create_center, create_station, center_data,\
    result_form_data, result_form_data_blank, TestBase
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.entry_version import EntryVersion


class TestDataEntryClerk(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()

    def _common_view_tests(self, view):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            view(request)
        self._create_and_login_user()
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request)
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def _post_enter_results(self, result_form):
        view = views.EnterResultsView.as_view()
        data = result_form_data(result_form)
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        return view(request)

    def test_data_entry_view(self):
        response = self._common_view_tests(views.DataEntryView.as_view())
        self.assertContains(response, 'Data Entry')
        self.assertIn('<form id="result_form"', response.content)

    def test_center_detail_center_number_length(self):
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1,
                                         center=center,
                                         station_number=station_number)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.CenterDetailsView.as_view()
        data = {'center_number': '1234', 'center_number': '1234'}
        session = {'result_form': result_form.pk}
        data.update(session)
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = session
        response = view(request)

        self.assertContains(response,
                            u'Ensure this value has at least 5 characters')

    def test_center_detail_center_not_equal(self):
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1,
                                         center=center,
                                         station_number=station_number)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.CenterDetailsView.as_view()
        data = center_data('12345', '12346')
        session = {'result_form': result_form.pk}
        data.update(session)
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = session
        response = view(request)
        self.assertContains(response, 'Center Numbers do not match')

    def test_center_detail_no_station(self):
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1,
                                         center=center,
                                         station_number=station_number)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.CenterDetailsView.as_view()
        session = {'result_form': result_form.pk}
        data = center_data(code)
        data.update(session)
        data.update({'station_number': 3, 'station_number_copy': 3})
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = session
        response = view(request)
        self.assertContains(response, 'Invalid Station Number for this Center')

    def test_center_detail_redirects_to_enter_results(self):
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1,
                                         center=center,
                                         station_number=station_number)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.CenterDetailsView.as_view()
        result_form_data = {'result_form': result_form.pk}
        data = center_data(code, station_number=station_number)
        data.update(result_form_data)
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = result_form_data
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('data-entry/enter-results',
                      response['location'])

    def test_center_detail_validates_clerk(self):
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_2,
                                         center=center,
                                         station_number=station_number)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.CenterDetailsView.as_view()
        result_form_data = {'result_form': result_form.pk}
        data = center_data(code, station_number=station_number)
        data.update(result_form_data)
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = result_form_data
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Data Entry 2')

    def test_enter_results_has_candidates(self):
        code = '12345'
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1)
        ballot = result_form.ballot
        candidate_name = 'candidate name'
        create_candidate(ballot, candidate_name)

        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.EnterResultsView.as_view()
        data = center_data(code)
        request = self.factory.get('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, candidate_name)

    def test_enter_results_invalid(self):
        code = '12345'
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1)
        ballot = result_form.ballot
        candidate_name = 'candidate name'
        create_candidate(ballot, candidate_name)

        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.EnterResultsView.as_view()
        data = result_form_data_blank(result_form)
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Missing votes')

    def test_enter_results_success_data_entry_one(self):
        code = '12345'
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1)
        ballot = result_form.ballot
        candidate_name = 'candidate name'
        create_candidate(ballot, candidate_name)

        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)

        response = self._post_enter_results(result_form)

        self.assertEqual(response.status_code, 302)
        self.assertIn('data-entry',
                      response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.DATA_ENTRY_2)

        reconciliation_forms = updated_result_form.reconciliationform_set.all()
        self.assertEqual(len(reconciliation_forms), 1)
        self.assertEqual(reconciliation_forms[0].entry_version,
                         EntryVersion.DATA_ENTRY_1)

        results = updated_result_form.results.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entry_version, EntryVersion.DATA_ENTRY_1)

        for result in results:
            self.assertEqual(result.user, self.user)

    def test_enter_results_success_data_entry_two(self):
        code = '12345'
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_2)
        ballot = result_form.ballot
        candidate_name = 'candidate name'
        create_candidate(ballot, candidate_name)

        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)

        response = self._post_enter_results(result_form)

        self.assertEqual(response.status_code, 302)
        self.assertIn('data-entry',
                      response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.CORRECTION)

        reconciliation_forms = updated_result_form.reconciliationform_set.all()
        self.assertEqual(len(reconciliation_forms), 1)

        self.assertEqual(reconciliation_forms[0].entry_version,
                         EntryVersion.DATA_ENTRY_2)

        results = updated_result_form.results.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entry_version, EntryVersion.DATA_ENTRY_2)
        self.assertEqual(results[0].user, self.user)

    def test_enter_results_success_data_entry(self):
        code = '12345'
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1)
        ballot = result_form.ballot
        candidate_name = 'candidate name'
        create_candidate(ballot, candidate_name)

        self._create_and_login_user('data_entry_1')
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.EnterResultsView.as_view()
        data = result_form_data(result_form)
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)

        data_entry_1 = self.user

        self._create_and_login_user('data_entry_2')
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('data-entry',
                      response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.CORRECTION)
        results = updated_result_form.results.filter(
            entry_version=EntryVersion.DATA_ENTRY_2)
        self.assertTrue(results.count() > 0)
        self.assertEqual(results.all()[0].user, self.user)
        results = updated_result_form.results.filter(
            entry_version=EntryVersion.DATA_ENTRY_2)
        self.assertTrue(results.count() > 0)

        for result in results:
            self.assertEqual(result.user, self.user)
            self.assertNotEqual(result.user, data_entry_1)
