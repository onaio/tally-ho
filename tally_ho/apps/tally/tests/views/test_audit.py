from django.core.exceptions import PermissionDenied
from django.core.serializers.json import json, DjangoJSONEncoder
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.utils import timezone

from tally_ho.apps.tally.views import audit as views
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    create_audit,
    create_result_form,
    create_recon_forms,
    create_candidates,
    create_reconciliation_form,
    create_tally,
    TestBase
)


class TestAudit(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self.encoded_result_form_audit_start_time =\
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))

    def _common_view_tests(self, view, tally=None):
        if not tally:
            tally = create_tally()
        request = self.factory.get('/')
        request.user = AnonymousUser()
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/accounts/login/?next=/', response['location'])
        self._create_and_login_user()
        tally.users.add(self.user)
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request, tally_id=tally.pk)
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        response = view(request, tally_id=tally.pk)
        response.render()
        self.assertIn(b'/accounts/logout/', response.content)
        return response

    def test_dashboard_get(self):
        response = self._common_view_tests(
            views.DashboardView.as_view())
        self.assertContains(response, 'Audit')

    def test_dashboard_get_supervisor(self):
        username = 'alice'
        self._create_and_login_user(username=username)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally,
                                         station_number=42)
        quarantine_check = QuarantineCheck.objects.create(
            user=self.user,
            name='Guard against overvoting',
            method='1',
            value=1)
        audit = create_audit(result_form, self.user, reviewed_team=True)
        audit.quarantine_checks.add(quarantine_check)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally.users.add(self.user)
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        view = views.DashboardView.as_view()
        response = view(request, tally_id=tally.pk)

        self.assertContains(response, '<th>Barcode</th>')
        self.assertContains(response, '<th>Center</th>')
        self.assertContains(response, '<th>Station</th>')
        self.assertContains(response, '<th>Race</th>')
        self.assertContains(response, '<th>Sub Race</th>')
        self.assertContains(response, '<th>Audit Team Reviewed By</th>')
        self.assertContains(response, '<th>Audit Supervisor Reviewed By</th>')
        self.assertContains(response, '<th>Action</th>')
        self.assertContains(response, username)
        self.assertContains(response, '42')

    def test_dashboard_get_csv(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        create_result_form(form_state=FormState.AUDIT,
                           tally=tally)
        view = views.DashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk, format='csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), 'text/csv')

    def test_dashboard_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.DashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('audit/review',
                      response['location'])

    def test_review_get(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session =\
            {'result_form':
             result_form.pk,
             'encoded_result_form_audit_start_time':
             self.encoded_result_form_audit_start_time}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forward to Supervisor')

    def test_review_get_supervisor(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session =\
            {'result_form':
             result_form.pk,
             'encoded_result_form_audit_start_time':
             self.encoded_result_form_audit_start_time}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mark Form as Resolved')
        self.assertContains(response, 'Return to Audit Team')

    def test_review_post_invalid(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        # an invalid enum choice
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 10,
                'resolution_recommendation': 0}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)

    def test_review_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 0}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = result_form.audit
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reviewed_team, False)
        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD)

    def test_review_post_audit_exists(self):
        self._create_and_login_user(username='alice')
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        create_audit(result_form, self.user)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = result_form.audit
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reviewed_team, False)
        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD)

    def test_review_post_forward(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'forward': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = result_form.audit
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reviewed_team, True)
        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD)

    def test_review_post_supervisor(self):
        # save audit as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        data['encoded_result_form_audit_start_time'] =\
            self.encoded_result_form_audit_start_time
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = result_form.audit
        self.assertEqual(audit.supervisor, self.user)
        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD)

    def test_review_post_supervisor_return(self):
        # save audit as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'return': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        data['encoded_result_form_audit_start_time'] =\
            self.encoded_result_form_audit_start_time
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = result_form.audit
        self.assertEqual(audit.supervisor, self.user)
        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD)
        self.assertEqual(audit.reviewed_team, False)

    def test_review_post_supervisor_implement(self):
        # save audit as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'forward': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 4,
            'implement': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        data['encoded_result_form_audit_start_time'] =\
            self.encoded_result_form_audit_start_time
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = result_form.audit
        self.assertEqual(audit.supervisor, self.user)
        self.assertEqual(audit.reviewed_supervisor, True)
        self.assertEqual(audit.reviewed_team, True)
        self.assertEqual(audit.for_superadmin, True)
        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD)

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        approved_by_supervisor =\
            audit.for_superadmin and audit.active
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         approved_by_supervisor)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         audit.reviewed_supervisor)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_check_audit_state_when_no_action_prior(self):
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'resolution_recommendation': 1,
            'implement': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        data['encoded_result_form_audit_start_time'] =\
            self.encoded_result_form_audit_start_time
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = Audit.objects.get(result_form=result_form)
        self.assertEqual(audit.reviewed_supervisor, True)
        self.assertNotEqual(audit.result_form.form_state,
                            FormState.AUDIT)
        self.assertEqual(audit.result_form.form_state,
                         FormState.DATA_ENTRY_1)

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        approved_by_supervisor =\
            audit.for_superadmin and audit.active
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         approved_by_supervisor)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         audit.reviewed_supervisor)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_supervisor_implement_de1(self):
        # save audit as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 0,
            'forward': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor and request copy from field
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 1,
            'resolution_recommendation': 1,
            'implement': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        data['encoded_result_form_audit_start_time'] =\
            self.encoded_result_form_audit_start_time
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = Audit.objects.get(result_form=result_form)
        self.assertEqual(audit.supervisor, self.user)
        self.assertFalse(audit.reviewed_supervisor)
        self.assertTrue(audit.reviewed_team)
        self.assertTrue(audit.active)
        self.assertEqual(audit.result_form.form_state,
                         FormState.AUDIT)
        self.assertEqual(len(audit.result_form.results.all()), 20)
        self.assertEqual(len(audit.result_form.reconciliationform_set.all()),
                         2)

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        approved_by_supervisor =\
            audit.for_superadmin and audit.active
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         approved_by_supervisor)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         audit.reviewed_supervisor)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

        for result in audit.result_form.results.all():
            self.assertTrue(result.active)

        for result in audit.result_form.reconciliationform_set.all():
            self.assertTrue(result.active)

        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD)

        # save as supervisor and return to data entry 1
        self._create_and_login_user(username='johndoe')
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 3,
            'resolution_recommendation': 1,
            'implement': 1,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        data['encoded_result_form_audit_start_time'] =\
            self.encoded_result_form_audit_start_time
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        audit = Audit.objects.get(result_form=result_form)
        self.assertEqual(audit.supervisor, self.user)
        self.assertTrue(audit.reviewed_supervisor)
        self.assertTrue(audit.reviewed_team)
        self.assertFalse(audit.active)
        self.assertEqual(audit.result_form.form_state,
                         FormState.DATA_ENTRY_1)
        self.assertEqual(len(audit.result_form.results.all()), 20)
        self.assertEqual(len(audit.result_form.reconciliationform_set.all()),
                         2)

        result_form_stat =\
            ResultFormStats.objects.filter(result_form=result_form).last()
        approved_by_supervisor =\
            audit.for_superadmin and audit.active
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         approved_by_supervisor)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         audit.reviewed_supervisor)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

        for result in audit.result_form.results.all():
            self.assertFalse(result.active)

        for result in audit.result_form.reconciliationform_set.all():
            self.assertFalse(result.active)

        self.assertEqual(audit.resolution_recommendation,
                         AuditResolution.NO_PROBLEM_TO_DE_1)
        self.assertEqual(audit.action_prior_to_recommendation,
                         ActionsPrior.NONE_REQUIRED)


    def test_create_audit_get(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)

        view = views.CreateAuditView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Audit')

    def test_create_audit_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        barcode = 123456789
        serial_number = 0
        auditable_states = [FormState.CORRECTION,
                            FormState.DATA_ENTRY_1,
                            FormState.DATA_ENTRY_2,
                            FormState.QUALITY_CONTROL]

        for form_state in auditable_states:
            result_form = create_result_form(form_state=form_state,
                                             barcode=barcode,
                                             tally=tally,
                                             serial_number=serial_number)
            create_recon_forms(result_form, self.user)
            create_candidates(result_form, self.user)
            view = views.CreateAuditView.as_view()
            data = {
                'barcode': result_form.barcode,
                'barcode_copy': result_form.barcode,
                'tally_id': tally.pk,
            }
            request = self.factory.post('/', data=data)
            request.user = self.user
            request.session = data
            response = view(request, tally_id=tally.pk)
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
                                         tally=tally,
                                         serial_number=serial_number)
        view = views.CreateAuditView.as_view()
        data = {
            'barcode': result_form.barcode,
            'barcode_copy': result_form.barcode,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_create_audit_post_super(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        tally = create_tally()
        tally.users.add(self.user)
        barcode = 123456789
        serial_number = 0
        auditable_states = [FormState.CORRECTION,
                            FormState.ARCHIVED,
                            FormState.DATA_ENTRY_1,
                            FormState.DATA_ENTRY_2,
                            FormState.QUALITY_CONTROL]

        for form_state in auditable_states:
            result_form = create_result_form(form_state=form_state,
                                             barcode=barcode,
                                             tally=tally,
                                             serial_number=serial_number)
            create_recon_forms(result_form, self.user)
            create_candidates(result_form, self.user)
            view = views.CreateAuditView.as_view()
            data = {
                'barcode': result_form.barcode,
                'barcode_copy': result_form.barcode,
                'tally_id': tally.pk,
            }
            request = self.factory.post('/', data=data)
            request.user = self.user
            request.session = data
            response = view(request, tally_id=tally.pk)
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
