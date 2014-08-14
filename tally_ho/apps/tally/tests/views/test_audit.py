from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from tally_ho.apps.tally.views import audit as views
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_audit,\
    create_result_form, create_recon_forms, create_candidates,\
    create_reconciliation_form, TestBase


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

    def test_dashboard_get_supervisor(self):
        username = 'alice'
        self._create_and_login_user(username=username)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         station_number=42)
        create_audit(result_form, self.user, reviewed_team=True)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        request = self.factory.get('/')
        request.user = self.user
        view = views.DashboardView.as_view()
        response = view(request)

        self.assertContains(response, 'Audit')
        self.assertContains(response, username)
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
        # an invalid enum choice
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 10,
                'resolution_recommendation': 0}
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
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 0}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = result_form.audit
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reviewed_team, False)
        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_audit_exists(self):
        self._create_and_login_user(username='alice')
        result_form = create_result_form(form_state=FormState.AUDIT)
        create_audit(result_form, self.user)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 0}
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
                'resolution_recommendation': 0,
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
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 0}
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
                'resolution_recommendation': 0}
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
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 0}
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
                'resolution_recommendation': 0,
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
                'resolution_recommendation': 0,
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
                'resolution_recommendation': 4,
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
        self._create_and_login_user()
        result_form = create_result_form(form_state=FormState.AUDIT)
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 0,
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
                'resolution_recommendation': 1,
                'implement': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        audit = Audit.objects.get(result_form=result_form)
        self.assertEqual(audit.supervisor, self.user)
        self.assertTrue(audit.reviewed_supervisor)
        self.assertTrue(audit.reviewed_team)
        self.assertFalse(audit.active)
        self.assertEqual(audit.result_form.form_state,
                         FormState.AUDIT)
        self.assertEqual(len(audit.result_form.results.all()), 20)
        self.assertEqual(len(audit.result_form.reconciliationform_set.all()),
                         2)

        for result in audit.result_form.results.all():
            self.assertFalse(result.active)

        for result in audit.result_form.reconciliationform_set.all():
            self.assertFalse(result.active)

        self.assertEqual(audit.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_create_audit_get(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        view = views.CreateAuditView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Audit')

    def test_create_audit_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        barcode = 123456789
        serial_number = 0
        auditable_states = [FormState.CORRECTION,
                            FormState.ARCHIVING,
                            FormState.DATA_ENTRY_1,
                            FormState.DATA_ENTRY_2,
                            FormState.QUALITY_CONTROL]

        for form_state in auditable_states:
            result_form = create_result_form(form_state=form_state,
                                             barcode=barcode,
                                             serial_number=serial_number)
            create_recon_forms(result_form, self.user)
            create_candidates(result_form, self.user)
            view = views.CreateAuditView.as_view()
            data = {'barcode': result_form.barcode,
                    'barcode_copy': result_form.barcode}
            request = self.factory.post('/', data=data)
            request.user = self.user
            request.session = data
            response = view(request)
            result_form.reload()

            self.assertEqual(response.status_code, 302)
            self.assertEqual(result_form.form_state, FormState.AUDIT)
            self.assertEqual(result_form.audited_count, 1)
            self.assertEqual(result_form.audit.user, self.user)

            for result in result_form.reconciliationform_set.all():
                self.assertFalse(result.active)

            for result in result_form.results.all():
                self.assertFalse(result.active)

            barcode = barcode + 1
            serial_number = serial_number + 1

        # not auditable state
        result_form = create_result_form(form_state=FormState.ARCHIVED,
                                         barcode=barcode,
                                         serial_number=serial_number)
        view = views.CreateAuditView.as_view()
        data = {'barcode': result_form.barcode,
                'barcode_copy': result_form.barcode}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)
        result_form.reload()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_create_audit_post_super(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        barcode = 123456789
        serial_number = 0
        auditable_states = [FormState.CORRECTION,
                            FormState.ARCHIVING,
                            FormState.ARCHIVED,
                            FormState.DATA_ENTRY_1,
                            FormState.DATA_ENTRY_2,
                            FormState.QUALITY_CONTROL]

        for form_state in auditable_states:
            result_form = create_result_form(form_state=form_state,
                                             barcode=barcode,
                                             serial_number=serial_number)
            create_recon_forms(result_form, self.user)
            create_candidates(result_form, self.user)
            view = views.CreateAuditView.as_view()
            data = {'barcode': result_form.barcode,
                    'barcode_copy': result_form.barcode}
            request = self.factory.post('/', data=data)
            request.user = self.user
            request.session = data
            response = view(request)
            result_form.reload()

            self.assertEqual(response.status_code, 302)
            self.assertEqual(result_form.form_state, FormState.AUDIT)
            self.assertEqual(result_form.audited_count, 1)
            self.assertEqual(result_form.audit.user, self.user)

            for result in result_form.reconciliationform_set.all():
                self.assertFalse(result.active)

            for result in result_form.results.all():
                self.assertFalse(result.active)

            barcode = barcode + 1
            serial_number = serial_number + 1
