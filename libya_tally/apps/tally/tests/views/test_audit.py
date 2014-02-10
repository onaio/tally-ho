from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import audit as views
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_result_form,\
    TestBase


class TestAudit(TestBase):
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
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_dashboard_get(self):
        response = self._common_view_tests(
            views.AuditDashboardView.as_view())
        self.assertContains(response, 'Audit')

    def test_dashboard_get_forms(self):
        create_result_form(form_state=FormState.AUDIT,
                           station_number=42)
        response = self._common_view_tests(
            views.AuditDashboardView.as_view())

        self.assertContains(response, 'Audit')
        self.assertContains(response, '42')

    def test_dashboard_post(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.AuditDashboardView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('audit/review',
                      response['location'])

    def test_review_get(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.AuditReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_review_post_invalid(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.AuditReviewView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)
        self.assertEqual(response.status_code, 200)
