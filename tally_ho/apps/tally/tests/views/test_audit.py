import csv

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder, json
from django.test import RequestFactory
from django.utils import timezone

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest
from tally_ho.apps.tally.views import audit as views
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.request_reason import RequestReason
from tally_ho.libs.models.enums.request_status import RequestStatus
from tally_ho.libs.models.enums.request_type import RequestType
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (TestBase, create_audit,
                                           create_candidates,
                                           create_recon_forms,
                                           create_reconciliation_form,
                                           create_result_form, create_tally,
                                           create_center, create_station,
                                           create_region)


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
        # Store initial state for tracking verification
        initial_state = result_form.form_state

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 0}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        # Reload to get updated values
        result_form.refresh_from_db()

        # Verify tracking - ReviewView sets user and previous_form_state
        self.assertEqual(result_form.user, self.user.userprofile)
        self.assertEqual(result_form.previous_form_state, initial_state)

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
            # Verify previous_form_state and user tracking
            self.assertEqual(result_form.previous_form_state, form_state)
            self.assertEqual(result_form.user, self.user.userprofile)
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
            # Verify previous_form_state and user tracking
            self.assertEqual(result_form.previous_form_state, form_state)
            self.assertEqual(result_form.user, self.user.userprofile)
            self.assertEqual(result_form.audited_count, 1)
            self.assertEqual(result_form.audit.user, self.user)

            for result in result_form.reconciliationform_set.all():
                self.assertFalse(result.active)

            for result in result_form.results.all():
                self.assertFalse(result.active)

            barcode = barcode + 1
            serial_number = serial_number + 1

    def test_print_cover_get(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        create_audit(result_form, self.user)

        view = views.PrintCoverView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Audit Case: Team Page')
        self.assertContains(response, self.user.username)
        self.assertContains(response, 'Problem')

    def test_print_cover_get_with_no_print_cover_in_audit(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        tally.print_cover_in_audit = False
        tally.save()
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        create_audit(result_form, self.user)

        view = views.PrintCoverView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {
            'result_form': result_form.pk,
            'encoded_result_form_audit_start_time':
                self.encoded_result_form_audit_start_time
        }
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response,
                             f'/audit/{tally.pk}/',
                             fetch_redirect_response=False)
        self.assertNotIn('result_form', request.session)
        self.assertTrue(ResultFormStats.objects.filter(
            result_form=result_form, user=self.user.userprofile).exists())
    def test_print_cover_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        create_audit(result_form, self.user)

        view = views.PrintCoverView.as_view()
        data = {'result_form': result_form.pk, 'tally_id': tally.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {
            'result_form': result_form.pk,
            'encoded_result_form_audit_start_time':
                self.encoded_result_form_audit_start_time
        }
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response,
                             f'/audit/{tally.pk}/',
                             fetch_redirect_response=False)
        self.assertNotIn('result_form', request.session)
        self.assertTrue(ResultFormStats.objects.filter(
            result_form=result_form, user=self.user.userprofile).exists())

    def test_audit_action_send_to_clearance(self):
        """Test audit_action creates Clearance when SEND_TO_CLEARANCE."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        tally = create_tally()
        tally.users.add(self.user)

        # Create a result form in AUDIT state
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=tally
        )
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)

        # Store initial state
        initial_state = result_form.form_state

        # Create audit with SEND_TO_CLEARANCE resolution
        audit = create_audit(result_form, self.user, reviewed_team=True)
        audit.resolution_recommendation = AuditResolution.SEND_TO_CLEARANCE
        audit.reviewed_supervisor = True
        audit.save()

        # Import Clearance model to check creation
        from tally_ho.apps.tally.models.clearance import Clearance

        # Verify no clearance exists yet
        self.assertEqual(
            Clearance.objects.filter(result_form=result_form).count(), 0
        )

        # Prepare the view and data for ReviewView which calls audit_action
        view = views.ReviewView.as_view()
        data = {
            'result_form': result_form.pk,
            'action_prior_to_recommendation': 0,  # No action prior
            'resolution_recommendation': 5,  # SEND_TO_CLEARANCE
            'implement': 1,  # Implement the resolution
            'tally_id': tally.pk,
        }

        request = self.factory.post('/', data=data)
        request.user = self.user
        data['encoded_result_form_audit_start_time'] = (
            self.encoded_result_form_audit_start_time
        )
        request.session = data

        # Execute the view which triggers audit_action
        response = view(request, tally_id=tally.pk)

        # Verify response is redirect
        self.assertEqual(response.status_code, 302)

        # Reload result form to get updated state
        result_form.refresh_from_db()

        # Verify form state changed to CLEARANCE
        self.assertEqual(result_form.form_state, FormState.CLEARANCE)

        # Verify previous_form_state tracking
        self.assertEqual(result_form.previous_form_state, initial_state)

        # Verify user tracking
        self.assertEqual(result_form.user, self.user.userprofile)

        # Verify reject_reason was set
        self.assertIn(
            "Audit action send to clearance", result_form.reject_reason
        )
        self.assertIn(self.user.username, result_form.reject_reason)

        # Verify Clearance was created
        clearances = Clearance.objects.filter(result_form=result_form)
        self.assertEqual(clearances.count(), 1)

        # Verify clearance details
        clearance = clearances.first()
        self.assertEqual(clearance.user, self.user.userprofile)
        self.assertTrue(clearance.active)

        # Verify audit is deactivated
        audit.refresh_from_db()
        self.assertFalse(audit.active)

        # Verify results and recon forms are deactivated (due to reject)
        for result in result_form.results.all():
            self.assertFalse(result.active)

        for recon in result_form.reconciliationform_set.all():
            self.assertFalse(recon.active)


class TestAuditRecallRequestsCsvView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_SUPERVISOR)
        self.tally = create_tally()
        self.tally.users.add(self.user)

    def test_audit_recall_requests_csv_get(self):
        result_form1 = create_result_form(tally=self.tally,
                                          form_state=FormState.ARCHIVED)
        result_form2 = create_result_form(tally=self.tally,
                                          form_state=FormState.ARCHIVED,
                                          barcode='987654321',
                                          serial_number=1)
        WorkflowRequest.objects.create(
            result_form=result_form1,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            request_reason=RequestReason.OTHER,
            requester=self.user.userprofile
        )
        WorkflowRequest.objects.create(
            result_form=result_form2,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            request_reason=RequestReason.DATA_ENTRY_ERROR,
            requester=self.user.userprofile,
            status=RequestStatus.APPROVED,
            approver=self.user.userprofile,
            resolved_date=timezone.now()
        )

        view = views.AuditRecallRequestsCsvView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="recall_requests.csv"',
                      response['Content-Disposition'])

        content = response.content.decode('utf-8')
        reader = csv.reader(content.splitlines())
        header = next(reader)
        self.assertEqual(header[0], 'Request ID')
        self.assertEqual(header[3], 'Barcode')
        self.assertEqual(header[9], 'Requested By')

        data_rows = list(reader)
        self.assertEqual(len(data_rows), 2)
        self.assertEqual(data_rows[0][3], result_form2.barcode)
        self.assertEqual(data_rows[1][3], result_form1.barcode)
        self.assertEqual(data_rows[1][2], 'Pending')

    def test_review_view_displays_quarantine_check_details_reconciliation(self):
        """Test that review view displays quarantine check
          details for reconciliation check."""
        self._create_and_login_user(username="audit_clerk")
        tally = create_tally()
        tally.users.add(self.user)
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        # Create result form with reconciliation form
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=tally
        )
        create_reconciliation_form(
            result_form,
            self.user,
            number_invalid_votes=10,
            number_sorted_and_counted=110,
            number_valid_votes=80
        )
        
        create_candidates(
            result_form=result_form,
            user=result_form.user,
            votes=20,
            num_results=2
        )
        
        result_form.save()

        # Create audit with quarantine check
        audit = create_audit(result_form, self.user)
        check = QuarantineCheck.objects.create(
            name="Reconciliation Check",
            method="pass_reconciliation_check",
            value=5,
            percentage=0
        )
        audit.quarantine_checks.add(check)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}

        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        content = response.rendered_content

        # Check that quarantine check name is displayed
        self.assertIn(check.name, content)

        # Check that actual values are displayed
        self.assertIn('<td>Total Valid Votes</td>', content)
        self.assertIn('<td class="result-column">80</td>', content)
        self.assertIn(
            '<td>Number of Invalid Ballot Papers</td>', 
            content
        )
        self.assertIn('<td class="result-column">10</td>', content)
        self.assertIn(
            '<td>Total Number of Ballot Papers in the Box</td>',
             content
        )
        self.assertIn('<td class="result-column">110</td>', content)
        self.assertIn('<td>Tolerance Percentage</td>', content)
        self.assertIn(
            '<td class="result-column">5 (fixed value)</td>', 
            content
        )
        

    def test_review_view_displays_quarantine_check_details_over_voting(self):
        """Test that review view displays quarantine check details 
        for over voting check."""
        
        self._create_and_login_user(username="audit_clerk")
        tally = create_tally()
        tally.users.add(self.user)
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        # Create station with registrants
        create_region(tally=tally)
        
        center = create_center("12345", tally=tally)
        station = create_station(registrants=80, tally=tally, center=center)

        # Create result form with reconciliation form
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=tally,
            center=center,
            station_number=station.station_number
        )
        create_reconciliation_form(
            result_form,
            self.user,
            number_invalid_votes=20
        )
        result_form.save()

        create_candidates(
            result_form=result_form,
            user=result_form.user,
            votes=20,
            num_results=2
        )

        # Create audit with over voting check
        audit = create_audit(result_form, self.user)
        check = QuarantineCheck.objects.create(
            name="Over Voting Check",
            method="pass_over_voting_check",
            value=10,
            percentage=0
        )
        audit.quarantine_checks.add(check)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}

        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        content = response.rendered_content

        # Check that quarantine check name is displayed
        self.assertIn(check.name, content)

        # Check that actual values are displayed        
        self.assertIn(
            '<td>Registered Voters</td>',
            content
        )
        self.assertIn(
            '<td class="result-column">80</td>',
            content
        )
        self.assertIn(
            '<td>Total Valid Votes</td>',
              content
        )
        self.assertIn(
            '<td>Number of Invalid Ballot Papers</td>', 
            content
        )
        self.assertIn(
            '<td class="result-column">20</td>',
            content
        )
        self.assertIn(
            '<td>Tolerance Percentage</td>',
            content
        )
        self.assertIn(
            '<td class="result-column">10 (fixed value)</td>',
            content
        )

    def test_review_view_displays_quarantine_check_details_card_check(self):
        """Test that review view displays quarantine check 
        details for card check."""
        self._create_and_login_user("audit_clerk")
        tally = create_tally()
        tally.users.add(self.user)
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        # Create result form with reconciliation form
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=tally
        )
        create_reconciliation_form(
            result_form,
            self.user,
            number_valid_votes=200,
            number_invalid_votes=15,
            number_of_voter_cards_in_the_ballot_box=210
        )

        # Create audit with card check
        audit = create_audit(result_form, self.user)
        check = QuarantineCheck.objects.create(
            name="Card Check",
            method="pass_card_check",
            value=8,
            percentage=0
        )
        audit.quarantine_checks.add(check)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}

        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        content = response.rendered_content

        # Check that quarantine check name is displayed
        self.assertIn(check.name, content)

        # Check that actual values are displayed
        self.assertIn(
            '<td>Voter Cards in Ballot Box</td>',
            content
        )
        self.assertIn(
            '<td class="result-column">210</td>',
            content
        )
        self.assertIn(
            '<td>Total Valid Votes</td>',
            content
        )
        self.assertIn(
            '<td class="result-column">200</td>',
            content
        )
        self.assertIn(
            '<td>Total Invalid Votes</td>',
            content
        )
        self.assertIn(
            '<td class="result-column">15</td>',
            content
        )
        self.assertIn(
            '<td>Tolerance Percentage</td>',
            content
        )
        self.assertIn(
            '<td class="result-column">8 (fixed value)</td>',
            content
        )

    def test_review_view_multiple_quarantine_checks(self):
        """Test that review view displays details for 
        multiple quarantine checks."""
        self._create_and_login_user("audit_clerk")
        tally = create_tally()
        tally.users.add(self.user)
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)

        # Create result form with reconciliation form
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=tally
        )
        create_reconciliation_form(
            result_form,
            self.user,
            number_valid_votes=90,
            number_invalid_votes=10,
            number_sorted_and_counted=110,
            number_of_voter_cards_in_the_ballot_box=110
        )

        result_form.save()

        create_candidates(
            result_form=result_form,
            user=result_form.user,
            votes=20,
            num_results=2
        )

        # Create audit with multiple checks
        audit = create_audit(result_form, self.user)

        check1 = QuarantineCheck.objects.create(
            name="Reconciliation Check",
            method="pass_reconciliation_check",
            value=5,
            percentage=0
        )
        check2 = QuarantineCheck.objects.create(
            name="Card Check",
            method="pass_card_check",
            value=8,
            percentage=0
        )

        audit.quarantine_checks.add(check1, check2)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}

        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        content = response.rendered_content

        # Check that both quarantine check names are displayed
        self.assertIn(check1.name, content)
        self.assertIn(check2.name, content)

        # Check that details for both checks are displayed       
        self.assertIn(
            '<td>Voter Cards in Ballot Box</td>', 
            content
        )
        self.assertIn(
            '<td class="result-column">110</td>', 
            content
        )
        self.assertIn(
            '<td>Total Valid Votes</td>', 
            content
        )
        self.assertIn(
            '<td class="result-column">90</td>', 
            content
        )
        self.assertIn(
            '<td>Total Invalid Votes</td>', 
            content
        )
        self.assertIn(
            '<td class="result-column">10</td>', 
            content
        )
        self.assertIn(
            '<td>Tolerance Percentage</td>', 
            content
        )
        self.assertIn(
            '<td class="result-column">8 (fixed value)</td>', 
            content
        )

