from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.views import intake_clerk as views
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_center,\
    create_result_form, create_station, TestBase


class TestIntakeClerk(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()

    def _common_view_tests(self, view):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/accounts/login/?next=/', response['location'])
        self._create_and_login_user()
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request)
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_center_detail_view(self):
        response = self._common_view_tests(views.CenterDetailsView.as_view())
        self.assertContains(response, 'Intake')
        self.assertContains(response, '<form id="result_form"')

    def test_center_detail_barcode_length(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CenterDetailsView.as_view()
        short_length_barcode_data = {'barcode': '1223', 'barcode_copy': '1223'}
        request = self.factory.post('/', data=short_length_barcode_data)
        request.user = self.user
        response = view(request)
        self.assertContains(response,
                            u'Ensure this value has at least 9 characters')

    def test_center_detail_barcode_not_equal(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CenterDetailsView.as_view()
        barcode_data = {'barcode': '123453789', 'barcode_copy': '123456789'}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        response = view(request)
        self.assertContains(response, 'Barcodes do not match')

    def test_center_detail_barcode_does_not_exist(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CenterDetailsView.as_view()
        barcode_data = {'barcode': '123456789', 'barcode_copy': '123456789'}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        response = view(request)
        self.assertContains(response, 'Barcode does not exist')

    def test_center_detail_redirects_to_check_center_details(self):
        barcode = '123456789'
        center = create_center()
        create_result_form(barcode,
                           form_state=FormState.UNSUBMITTED,
                           center=center)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CenterDetailsView.as_view()
        barcode_data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('intake/check-center-details',
                      response['location'])
        result_form = ResultForm.objects.get(barcode=barcode)
        self.assertEqual(result_form.form_state, FormState.INTAKE)
        self.assertEqual(result_form.user, self.user)

    def test_center_detail_redirects_no_center(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.UNSUBMITTED)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CenterDetailsView.as_view()
        barcode_data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('intake/enter-center',
                      response['location'])
        result_form = ResultForm.objects.get(barcode=barcode)
        self.assertEqual(result_form.form_state, FormState.INTAKE)
        self.assertEqual(result_form.user, self.user)

    def test_enter_center_get(self):
        result_form = create_result_form(form_state=FormState.INTAKE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.EnterCenterView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Double Enter Center Details')

    def test_enter_center_post_invalid(self):
        result_form = create_result_form(form_state=FormState.INTAKE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.EnterCenterView.as_view()
        request = self.factory.post('/',
                                    data={'result_form': result_form.pk})
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Double Enter Center Details')

    def test_enter_center_post_valid(self):
        center = create_center(code='11111')
        create_station(center)
        result_form = create_result_form(form_state=FormState.INTAKE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.EnterCenterView.as_view()
        data = {'result_form': result_form.pk,
                'center_number': center.code,
                'center_number_copy': center.code,
                'station_number': 1,
                'station_number_copy': 1}
        request = self.factory.post('/',
                                    data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/intake/check-center-details', response['location'])

    def test_check_center_details(self):
        barcode = '123456789'
        result_form = create_result_form(barcode,
                                         form_state=FormState.UNSUBMITTED)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CheckCenterDetailsView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        with self.assertRaises(Exception):
            response = view(request)
        result_form.form_state = FormState.INTAKE
        result_form.save()
        response = view(request)
        self.assertContains(response, 'Check Center Details Against Form')
        self.assertIn('result_form', response.context_data)
        self.assertEqual(int(barcode),
                         response.context_data['result_form'].barcode)

    def test_intake_clerk_selects_matches(self):
        barcode = '123456789'
        result_form = create_result_form(barcode)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CheckCenterDetailsView.as_view()
        post_data = {'result_form': result_form.pk, 'is_match': 'true'}
        request = self.factory.post('/', data=post_data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        with self.assertRaises(Exception):
            response = view(request)
        result_form.form_state = FormState.INTAKE
        result_form.save()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/intake/printcover', response['location'])

    def _create_or_login_intake_clerk(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)

    def test_selects_no_matches(self):
        result_form = create_result_form()
        self._create_or_login_intake_clerk()
        view = views.CheckCenterDetailsView.as_view()
        post_data = {'result_form': result_form.pk, 'is_not_match': 'true'}
        request = self.factory.post('/', data=post_data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        with self.assertRaises(Exception):
            response = view(request)
        result_form.form_state = FormState.INTAKE
        result_form.save()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/intake/clearance', response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.CLEARANCE)

    def test_print_cover_invalid_state(self):
        result_form = create_result_form()
        self._create_or_login_intake_clerk()
        view = views.PrintCoverView.as_view()
        self.request.user = self.user
        self.request.session = {'result_form': result_form.pk}
        with self.assertRaises(SuspiciousOperation):
            view(self.request)

    def test_print_cover_get(self):
        result_form = create_result_form()
        self._create_or_login_intake_clerk()
        view = views.PrintCoverView.as_view()
        self.request.user = self.user
        self.request.session = {'result_form': result_form.pk}
        result_form.form_state = FormState.INTAKE
        result_form.save()
        response = view(self.request)
        expected_strings = [
            'Intake: Successful', '>Print</button>',
            'Data Entry One:', 'Data Entry Two:', 'To Quality Control [ ]'
        ]
        for test_string in expected_strings:
            self.assertContains(response, test_string)

    def test_print_cover_post(self):
        result_form = create_result_form()
        result_form.form_state = FormState.INTAKE
        result_form.save()
        self._create_or_login_intake_clerk()
        view = views.PrintCoverView.as_view()

        request = self.factory.post('/', data={'result_form': result_form.pk})
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('', response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(request.session.get('result_form'),
                         result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.DATA_ENTRY_1)

    def test_clearance(self):
        result_form = create_result_form()
        self._create_or_login_intake_clerk()
        view = views.ClearanceView.as_view()
        self.request.user = self.user
        self.request.session = {'result_form': result_form.pk}
        with self.assertRaises(Exception):
            response = view(self.request)
        result_form.form_state = FormState.INTAKE
        result_form.save()
        result_form.form_state = FormState.CLEARANCE
        result_form.save()
        response = view(self.request)
        self.assertContains(response,
                            'Form Sent to Clearance. Pass to Supervisor')
