from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import audit as views
from libya_tally.apps.tally.models.audit import Audit
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_result_form, TestBase


def create_audit(result_form, user):
    return Audit.objects.create(result_form=result_form,
                                user=user)


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
            views.DashboardView.as_view())
        self.assertContains(response, 'Audit')

    def test_dashboard_get_forms(self):
        create_result_form(form_state=FormState.AUDIT,
                           station_number=42)
        response = self._common_view_tests(
            views.DashboardView.as_view())

        self.assertContains(response, 'Audit')
        self.assertContains(response, '42')

    def test_dashboard_post(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.DashboardView.as_view()
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

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forward to Supervisor')

    def test_review_get_supervisor(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Implement Recommendation')
        self.assertContains(response, 'Return to Audit Team')

    def test_review_post_invalid(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_review_post(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = result_form.audit
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reviewed_team, False)
        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_forward(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'forward': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = result_form.audit
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reviewed_team, True)
        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_supervisor(self):
        # save audit as clerk
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = result_form.audit
        self.assertEqual(audit.supervisor, self.user)
        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_supervisor_return(self):
        # save audit as clerk
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'return': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = result_form.audit
        self.assertEqual(audit.supervisor, self.user)
        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(audit.reviewed_team, False)
        self.assertEqual(response.status_code, 302)

    def test_review_post_supervisor_implement(self):
        # save audit as clerk
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'forward': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 3,
                'implement': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = result_form.audit
        self.assertEqual(audit.supervisor, self.user)
        self.assertEqual(audit.reviewed_supervisor, True)
        self.assertEqual(audit.reviewed_team, True)
        self.assertEqual(audit.for_superadmin, True)
        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_supervisor_implement_de1(self):
        # save audit as clerk
        result_form = create_result_form(form_state=FormState.AUDIT)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'forward': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 1,
                'implement': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = Audit.objects.get(result_form=result_form)
        self.assertEqual(audit.supervisor, self.user)
        self.assertEqual(audit.reviewed_supervisor, True)
        self.assertEqual(audit.reviewed_team, True)
        self.assertEqual(audit.active, False)
        self.assertEqual(audit.result_form.form_state, FormState.DATA_ENTRY_1)
        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)
