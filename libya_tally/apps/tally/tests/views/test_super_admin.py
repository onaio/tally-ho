from django.core.exceptions import SuspiciousOperation
from django.test import RequestFactory

from libya_tally.apps.tally.views import super_admin as views
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_audit, create_clearance,\
    create_result_form, TestBase


class TestSuperAdmin(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_form_action_view_post_invalid_audit(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}

        with self.assertRaises(SuspiciousOperation):
            view(request)

    def test_form_action_view_post_review_audit(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk,
                'review': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/audit/review', response['Location'])

    def test_form_action_view_post_confirm_audit(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        audit = create_audit(result_form, self.user)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk,
                'confirm': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request)

        audit.reload()
        result_form.reload()
        self.assertEqual(audit.active, False)
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/super-administrator/form-action-list',
                      response['Location'])

    def test_form_action_view_post_review_clearance(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk,
                'review': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/clearance/review', response['Location'])

    def test_form_action_view_post_confirm_clearance(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        clearance = create_clearance(result_form, self.user)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk,
                'confirm': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request)

        clearance.reload()
        result_form.reload()
        self.assertEqual(clearance.active, False)
        self.assertEqual(result_form.form_state, FormState.INTAKE)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/super-administrator/form-action-list',
                      response['Location'])
