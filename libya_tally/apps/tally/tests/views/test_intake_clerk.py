from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally import views
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import TestBase
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState


class TestIntakeClerkView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.IntakeClerkView.as_view()
        self._create_permission_groups()

    def _common_view_tests(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            self.view(request)
        self._create_and_login_user()
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            self.view(request)
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        response = self.view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_intake_page(self):
        response = self._common_view_tests()
        self.assertContains(response, '<h1>Intake Dashboard</h1>')
        self.assertIn('"/intake/center-details"', response.content)

    def test_center_detail_view(self):
        self.view = views.CenterDetailView.as_view()
        response = self._common_view_tests()
        self.assertContains(response, 'Double Enter Center Details')
        self.assertIn('<form id="barcode_form"', response.content)

    def test_center_detail_barcode_length(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        self.view = views.CenterDetailView.as_view()
        short_length_barcode_data = {'barcode': '1223', 'barcode_copy': '1223'}
        request = self.factory.post('/', data=short_length_barcode_data)
        request.user = self.user
        response = self.view(request)
        self.assertContains(response,
                            u'Ensure this value has at least 9 characters')

    def test_center_detail_barcode_not_equal(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        self.view = views.CenterDetailView.as_view()
        barcode_data = {'barcode': '123453789', 'barcode_copy': '123456789'}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        response = self.view(request)
        self.assertContains(response, 'Barcodes do not match')

    def test_center_detail_barcode_does_not_exist(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        self.view = views.CenterDetailView.as_view()
        barcode_data = {'barcode': '123456789', 'barcode_copy': '123456789'}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        response = self.view(request)
        self.assertContains(response, 'Barcode does not exist')

    def test_center_detail_redirects_to_check_center_details(self):
        barcode = '123456789'
        ResultForm.objects.get_or_create(
            barcode=barcode, serial_number=0,
            form_state=FormState.UNSUBMITTED)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        self.view = views.CenterDetailView.as_view()
        barcode_data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        response = self.view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('intake/check-center-details/%s' % barcode,
                      response['location'])

    def test_check_center_details(self):
        barcode = '123456789'
        ResultForm.objects.get_or_create(
            barcode=barcode, serial_number=0,
            form_state=FormState.UNSUBMITTED)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        self.view = views.CheckCenterDetailView.as_view()
        barcode_data = {'barcode': barcode}
        request = self.factory.get('/', data=barcode_data)
        request.user = self.user
        response = self.view(request)
        self.assertContains(response, 'Check Centre Details Against Form')
        self.assertIn('result_form', response.context_data)
        self.assertEqual(int(barcode),
                         response.context_data['result_form'].barcode)
