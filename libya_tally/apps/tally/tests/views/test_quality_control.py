from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import quality_control as views
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_result_form, TestBase


class TestQualityControl(TestBase):
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
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_quality_control_get(self):
        response = self._common_view_tests(views.QualityControlView.as_view())
        self.assertContains(response, 'Quality Control')
        self.assertIn('<form id="result_form"', response.content)

    def test_quality_control_post(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlView.as_view()
        data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/dashboard',
                      response['location'])
        result_form = ResultForm.objects.get(barcode=barcode)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)
        self.assertEqual(result_form.quality_control.user, self.user)
