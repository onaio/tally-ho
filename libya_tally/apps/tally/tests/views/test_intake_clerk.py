from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import intake_clerk as views
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import TestBase
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState


class TestIntakeClerkView(TestBase):
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
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_intake_page(self):
        response = self._common_view_tests(views.IntakeClerkView.as_view())
        self.assertContains(response, '<h1>Intake Dashboard</h1>')
        self.assertIn('"/intake/center-details"', response.content)

    def test_center_detail_view(self):
        response = self._common_view_tests(views.CenterDetailsView.as_view())
        self.assertContains(response, 'Double Enter Center Details')
        self.assertIn('<form id="barcode_form"', response.content)

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
        ResultForm.objects.get_or_create(
            barcode=barcode, serial_number=0,
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
        self.assertIn('intake/check-center-details',
                      response['location'])
        result_form = ResultForm.objects.get(barcode=barcode)
        self.assertEqual(result_form.form_state, FormState.INTAKE)

    def test_check_center_details(self):
        barcode = '123456789'
        result_form, c = ResultForm.objects.get_or_create(
            barcode=barcode, serial_number=0,
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
        self.assertContains(response, 'Check Centre Details Against Form')
        self.assertIn('result_form', response.context_data)
        self.assertEqual(int(barcode),
                         response.context_data['result_form'].barcode)

    def test_intake_clerk_selects_matches(self):
        barcode = '123456789'
        result_form, c = ResultForm.objects.get_or_create(
            barcode=barcode, serial_number=0,
            form_state=FormState.UNSUBMITTED)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CheckCenterDetailsView.as_view()
        post_data = {'match': result_form.pk}
        request = self.factory.post('/', data=post_data)
        request.user = self.user
        request.session = {}
        with self.assertRaises(Exception):
            response = view(request)
        result_form.form_state = FormState.INTAKE
        result_form.save()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/intake/printcover', response['location'])

    def test_intake_clerk_selects_no_matches(self):
        barcode = '123456789'
        result_form, c = ResultForm.objects.get_or_create(
            barcode=barcode, serial_number=0,
            form_state=FormState.UNSUBMITTED)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        view = views.CheckCenterDetailsView.as_view()
        post_data = {'no_match': result_form.pk}
        request = self.factory.post('/', data=post_data)
        request.user = self.user
        request.session = {}
        with self.assertRaises(Exception):
            response = view(request)
        result_form.form_state = FormState.INTAKE
        result_form.save()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/intake/clearance', response['location'])
