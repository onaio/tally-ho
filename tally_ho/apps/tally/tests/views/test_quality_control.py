from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.serializers.json import json, DjangoJSONEncoder
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.urls import reverse
from django.test import RequestFactory
from django.utils import timezone

from tally_ho.apps.tally.views import quality_control as views
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    create_candidates,
    create_electrol_race,
    create_reconciliation_form,
    create_recon_forms,
    create_result_form,
    create_center,
    create_station,
    create_audit,
    create_tally,
    create_ballot,
    create_quality_control,
    create_quarantine_checks,
    TestBase,
)
from tally_ho.libs.tests.fixtures.electrol_race_data import (
    electrol_races
)

class TestQualityControl(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.encoded_result_form_qa_control_start_time =\
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))
        self.quarantine_data = getattr(settings, 'QUARANTINE_DATA')
        self.electrol_race = create_electrol_race(
            self.tally,
            **electrol_races[0]
        )

    def _common_view_tests(self, view):
        """
        Test common view
        """
        request = self.factory.get('/')
        request.session = {}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/accounts/login/?next=/', response['location'])
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request, tally_id=self.tally.pk)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        response = view(request, tally_id=self.tally.pk)
        response.render()
        self.assertIn(b'/accounts/logout/', response.content)
        return response

    def test_quality_control_get(self):
        """
        Test quality control view get
        """
        response = self._common_view_tests(views.QualityControlView.as_view())
        self.assertContains(response, 'Quality Control')
        self.assertIn(b'<form id="result_form"', response.content)

    def test_quality_control_post(self):
        """
        Test quality control view post
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlView.as_view()
        data = {
            'barcode': barcode,
            'barcode_copy': barcode,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/dashboard',
                      response['location'])
        result_form = ResultForm.objects.get(barcode=barcode)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)
        self.assertEqual(result_form.qualitycontrol.user, self.user)

    def test_dashboard_abort_post(self):
        """
        Test dashboard abort post
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'abort': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        quality_control = result_form.qualitycontrol_set.all()[0]

        self.assertEqual(quality_control.active, False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        self.assertEqual(request.session, {})

    def test_dashboard_incorrect_post_when_form_marked_for_release(self):
        """
        Test dashboard incorrrect post when form marked for release
        """
        barcode = '123456789'
        ballot = create_ballot(self.tally, available_for_release=True)
        create_result_form(barcode,
                           ballot=ballot,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'incorrect': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        quality_control = result_form.qualitycontrol_set.all()[0]
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)

        self.assertTrue(quality_control.active)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/confirm-reject',
                      response['location'])

    def test_dashboard_incorrect_post_when_form_not_marked_for_release(self):
        """
        Test dashboard incorrrect post when form not marked for release
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'incorrect': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/reject',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertFalse(quality_control.active)
        self.assertEqual(request.session, {})

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_dashboard_submit_post(self):
        """
        Test dashboard submit post
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        quality_control = create_quality_control(result_form, self.user)
        quality_control.passed_general = False
        quality_control.passed_reconciliation = False
        quality_control.passed_women = False
        quality_control.save()

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'correct': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        result_form = ResultForm.objects.get(pk=result_form.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/print',
                      response['location'])
        quality_control = result_form.qualitycontrol
        self.assertTrue(quality_control.passed_qc)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)

    def test_dashboard_get_double_recon(self):
        """
        Test dashboard get double recon
        """
        barcode = '123456789'
        center = create_center(tally=self.tally)
        station = create_station(center=center)
        result_form = create_result_form(barcode,
                                         center=center,
                                         station_number=station.station_number,
                                         tally=self.tally,
                                         form_state=FormState.QUALITY_CONTROL,
                                         electrol_race=self.electrol_race)
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.electrol_race.election_level)
        self.assertContains(response, self.electrol_race.ballot_name)
        self.assertContains(response, 'Cancel')

    def test_dashboard_get_double_recon_raise(self):
        """
        Test dashboard get double recon raise
        """
        barcode = '123456789'
        center = create_center(tally=self.tally)
        station = create_station(center=center)
        result_form = create_result_form(barcode,
                                         center=center,
                                         station_number=station.station_number,
                                         tally=self.tally,
                                         form_state=FormState.QUALITY_CONTROL)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.post('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}

        with self.assertRaises(SuspiciousOperation):
            view(request, tally_id=self.tally.pk)

    def test_dashboard_get(self):
        """
        Test dashboard get
        """
        barcode = '123456789'
        center = create_center(tally=self.tally)
        station = create_station(center=center)
        create_result_form(barcode,
                           center=center,
                           station_number=station.station_number,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL,
                           electrol_race=self.electrol_race)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.electrol_race.election_level)
        self.assertContains(response, self.electrol_race.ballot_name)
        self.assertNotContains(response, 'Reconciliation')
        self.assertContains(response, 'Cancel')

    def test_confirm_form_reset_view_post(self):
        """
        Test confirm form reset view post
        """
        barcode = '123456789'
        ballot = create_ballot(self.tally, available_for_release=True)
        create_result_form(barcode,
                           tally=self.tally,
                           ballot=ballot,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.ConfirmFormResetView.as_view()
        reject_reason = 'Form Incorrect'
        data = {
            'reject_reason': reject_reason
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)
        result_form = ResultForm.objects.get(pk=result_form.pk)
        quality_control = result_form.qualitycontrol_set.all()[0]

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/reject',
                      response['location'])
        self.assertEqual(request.session, {})
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)
        self.assertEqual(result_form.rejected_count, 1)
        self.assertEqual(result_form.reject_reason, reject_reason)
        self.assertFalse(quality_control.active)
        self.assertFalse(quality_control.passed_reconciliation)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_reconciliation_get(self):
        """
        Test reconciliation get
        """
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL,
                           tally=self.tally)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_reconciliation_form(result_form, self.user)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reconciliation')
        self.assertContains(response, 'Total number of the sorted and counted')

    def test_reconciliation_post_correct(self):
        """
        Test reconciliation post correct
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'correct': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/print',
                      response['location'])
        quality_control = QualityControl.objects.get(
            pk=result_form.qualitycontrol.pk)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)
        self.assertTrue(quality_control.passed_reconciliation)

    def test_reconciliation_post_incorrect_ballot_released(self):
        """
        Test reconciliation post incorrect ballot released
        """
        barcode = '123456789'
        ballot = create_ballot(self.tally, available_for_release=True)
        create_result_form(barcode,
                           tally=self.tally,
                           ballot=ballot,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_recon_forms(result_form, self.user)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'incorrect': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/confirm-reject',
                      response['location'])
        result_form = ResultForm.objects.get(pk=result_form.pk)
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertTrue(quality_control.active)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)
        self.assertEqual(result_form.rejected_count, 0)

    def test_reconciliation_post_incorrect_ballot_not_released(self):
        """
        Test reconciliation post incorrect ballot not released
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_recon_forms(result_form, self.user)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'incorrect': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/reject',
                      response['location'])
        self.assertEqual(result_form.rejected_count, 0)
        result_form = ResultForm.objects.get(pk=result_form.pk)
        quality_control = result_form.qualitycontrol_set.all()[0]

        results = result_form.results.all()
        self.assertTrue(len(results) > 0)

        for result in results:
            self.assertEqual(result.active, False)

        recon_forms = result_form.reconciliationform_set.all()
        self.assertTrue(len(recon_forms) > 0)

        for recon in recon_forms:
            self.assertEqual(recon.active, False)

        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)
        self.assertEqual(result_form.rejected_count, 1)
        self.assertEqual(quality_control.active, False)
        self.assertEqual(quality_control.passed_reconciliation, False)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_reconciliation_post_abort(self):
        """
        Test reconciliation post abort
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'abort': 1,
            'tally_id': self.tally.id,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertEqual(quality_control.active, False)

    def test_qc_view_get(self):
        """
        Test quality control view get
        """
        barcode = '123456789'
        center = create_center(tally=self.tally)
        station = create_station(center=center)
        create_result_form(barcode,
                           center=center,
                           station_number=station.station_number,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        name = 'the candidate name'
        women_name = 'women candidate name'
        votes = 123

        create_candidates(result_form, self.user, name, votes, women_name)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.electrol_race.election_level)
        self.assertContains(response, self.electrol_race.ballot_name)
        self.assertContains(response, name)
        self.assertContains(response, women_name)
        self.assertContains(response, str(votes))

    def test_qc_view_post_correct(self):
        """
        Test quality control view post correct
        """
        barcode = '123456789'
        result_form = create_result_form(barcode,
                                         tally=self.tally,
                                         form_state=FormState.QUALITY_CONTROL)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'correct': 1,
            'tally_id': self.tally.id,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/print',
                      response['location'])
        quality_control = QualityControl.objects.get(
            pk=result_form.qualitycontrol.pk)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)
        self.assertTrue(quality_control.passed_qc)

    def test_qc_view_post_incorrect_ballot_released(self):
        """
        Test quality control view post incorrect ballot released
        """
        barcode = '123456789'
        ballot = create_ballot(self.tally, available_for_release=True)
        create_result_form(barcode,
                           tally=self.tally,
                           ballot=ballot,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'incorrect': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/confirm-reject',
                      response['location'])
        result_form = ResultForm.objects.get(pk=result_form.pk)
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertTrue(quality_control.active)
        self.assertFalse(quality_control.passed_qc)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)
        self.assertEqual(result_form.rejected_count, 0)

    def test_qc_view_post_incorrect_ballot_not_released(self):
        """
        Test quality control view post incorrect ballot not released
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'incorrect': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/reject',
                      response['location'])
        self.assertEqual(result_form.rejected_count, 0)
        result_form = ResultForm.objects.get(pk=result_form.pk)
        quality_control = result_form.qualitycontrol_set.all()[0]

        results = result_form.results.all()
        self.assertTrue(len(results) > 0)

        for result in results:
            self.assertEqual(result.active, False)

        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)
        self.assertEqual(result_form.rejected_count, 1)
        self.assertEqual(quality_control.active, False)
        self.assertEqual(quality_control.passed_qc, False)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_qc_view_post_abort(self):
        """
        Test quality control view post abort
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'result_form': result_form.pk,
            'abort': 1,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertEqual(quality_control.active, False)

    def test_quality_control_post_passes_all_quarantine_triggers(self):
        """
        Test quality control post passes all quarantine triggers
        """
        create_quarantine_checks(self.quarantine_data)
        center = create_center()
        station = create_station(center=center,
                       registrants=50)
        result_form = create_result_form(
            form_state=FormState.QUALITY_CONTROL,
            center=center,
            tally=self.tally,
            station_number=station.station_number)
        recon_form =\
                    create_reconciliation_form(
                        result_form=result_form,
                        user=self.user,
                        number_unstamped_ballots=0,
                        number_invalid_votes=0,
                        number_valid_votes=50,
                        number_ballots_inside_box=50,
                        number_of_voter_cards_in_the_ballot_box=50,
                        total_of_cancelled_ballots_and_ballots_inside_box=50,
                        number_sorted_and_counted=50,
                    )
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user, votes=25, num_results=1)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'correct': 1,
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(
            result_form.num_votes,
            recon_form.total_of_cancelled_ballots_and_ballots_inside_box)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(result_form.form_state, FormState.AUDIT)
        self.assertIsNone(result_form.audit)
        self.assertEqual(result_form.audited_count, 0)
        self.assertIn('quality-control/print', response['location'])

    def test_quality_control_post_fails_registrants_quarantine_trigger(self):
        """
        Test quality control post fails registrants quarantine trigger
        """
        create_quarantine_checks(self.quarantine_data)
        center = create_center()
        station = create_station(
                        center=center,
                        registrants=40)
        result_form = create_result_form(
            form_state=FormState.QUALITY_CONTROL,
            center=center,
            tally=self.tally,
            station_number=station.station_number)
        create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_unstamped_ballots=0,
            number_invalid_votes=0,
            number_valid_votes=50,
            number_ballots_inside_box=50,
            number_of_voter_cards_in_the_ballot_box=50,
            total_of_cancelled_ballots_and_ballots_inside_box=50,
            number_sorted_and_counted=50,
        )
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user, votes=25, num_results=1)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'correct': 1,
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(result_form.audit)
        self.assertEqual(result_form.audited_count, 1)
        self.assertEqual(
            [c.method for c in result_form.audit.quarantine_checks.all()],
            ['pass_registrants_trigger'])
        self.assertIn('quality-control/print', response['location'])

    def test_quality_control_post_fails_voter_cards_quarantine_trigger(self):
        """
        Test quality control post fails voter cards quarantine trigger
        """
        create_quarantine_checks(self.quarantine_data)
        center = create_center()
        station = create_station(
                        center=center,
                        registrants=50)
        result_form = create_result_form(
            form_state=FormState.QUALITY_CONTROL,
            center=center,
            tally=self.tally,
            station_number=station.station_number)
        create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_unstamped_ballots=0,
            number_invalid_votes=0,
            number_valid_votes=50,
            number_ballots_inside_box=50,
            number_of_voter_cards_in_the_ballot_box=40,
            total_of_cancelled_ballots_and_ballots_inside_box=50,
            number_sorted_and_counted=50,
        )
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user, votes=25, num_results=1)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'correct': 1,
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(result_form.audit)
        self.assertEqual(result_form.audited_count, 1)
        self.assertEqual(
            [c.method for c in result_form.audit.quarantine_checks.all()],
            ['pass_voter_cards_trigger'])
        self.assertIn('quality-control/print', response['location'])

    def test_quality_control_post_fails_ballot_papers_quarantine_trigger(self):
        """
        Test quality control post fails ballot papers quarantine trigger
        """
        create_quarantine_checks(self.quarantine_data)
        center = create_center()
        station = create_station(
                        center=center,
                        registrants=50)
        result_form = create_result_form(
            form_state=FormState.QUALITY_CONTROL,
            center=center,
            tally=self.tally,
            station_number=station.station_number)
        create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_unstamped_ballots=0,
            number_invalid_votes=0,
            number_valid_votes=50,
            number_ballots_inside_box=50,
            number_of_voter_cards_in_the_ballot_box=50,
            total_of_cancelled_ballots_and_ballots_inside_box=50,
            number_sorted_and_counted=50,
            number_ballots_received=49,
            number_ballots_inside_and_outside_box=50,
        )
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user, votes=25, num_results=1)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'correct': 1,
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(result_form.audit)
        self.assertEqual(result_form.audited_count, 1)
        self.assertEqual(
            [c.method for c in result_form.audit.quarantine_checks.all()],
            ['pass_ballot_papers_trigger'])
        self.assertIn('quality-control/print', response['location'])

    def test_quality_control_post_fails_ballot_inside_quarantine_trigger(self):
        """
        Test quality control post fails ballot inside the box quarantine
        trigger
        """
        create_quarantine_checks(self.quarantine_data)
        center = create_center()
        station = create_station(
                        center=center,
                        registrants=50)
        result_form = create_result_form(
            form_state=FormState.QUALITY_CONTROL,
            center=center,
            tally=self.tally,
            station_number=station.station_number)
        create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_unstamped_ballots=1,
            number_invalid_votes=0,
            number_valid_votes=50,
            number_ballots_inside_box=50,
            number_of_voter_cards_in_the_ballot_box=50,
            total_of_cancelled_ballots_and_ballots_inside_box=50,
            number_sorted_and_counted=50,
            number_ballots_received=50,
            number_ballots_inside_and_outside_box=50,
        )
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user, votes=25, num_results=1)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'correct': 1,
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(result_form.audit)
        self.assertEqual(result_form.audited_count, 1)
        self.assertEqual(
            [c.method for c in result_form.audit.quarantine_checks.all()],
            ['pass_ballot_inside_box_trigger'])
        self.assertIn('quality-control/print', response['location'])

    def test_quality_control_post_quarantine(self):
        """
        Test quality control post
        """
        center = create_center()
        create_station(center, registrants=2)
        create_quarantine_checks(self.quarantine_data)
        result_form = create_result_form(
            form_state=FormState.QUALITY_CONTROL,
            tally=self.tally,
            center=center,
            station_number=1)
        create_reconciliation_form(
            result_form, self.user, number_valid_votes=2)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {
            'correct': 1,
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(result_form.form_state, FormState.AUDIT)
        self.assertTrue(result_form.audit)
        self.assertEqual(
            result_form.audit.quarantine_checks.count(),
            2)
        self.assertEqual(
            [c.method for c in result_form.audit.quarantine_checks.all()],
            ['pass_ballot_inside_box_trigger',
             'pass_candidates_votes_trigger'])
        self.assertEqual(result_form.audit.user, self.user)
        self.assertEqual(result_form.audited_count, 1)
        self.assertIn('quality-control/print', response['location'])

    def test_print_success_get(self):
        """
        Test print success get
        """
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.QUALITY_CONTROL,
                                         center=center,
                                         tally=self.tally,
                                         station_number=station_number)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.PrintView.as_view()
        request = self.factory.get('/')
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successful Archive')

    def test_print_quarantine_get(self):
        """
        Test print quarantine get
        """
        code = '12345'
        station_number = 1
        center = create_center(code, tally=self.tally)
        create_station(center)
        result_form = create_result_form(form_state=FormState.QUALITY_CONTROL,
                                         center=center,
                                         tally=self.tally,
                                         station_number=station_number)
        quarantine_check = QuarantineCheck.objects.create(
            user=self.user,
            name='1',
            method='1',
            value=1)
        audit = create_audit(result_form, self.user)
        audit.quarantine_checks.add(quarantine_check)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.PrintView.as_view()
        request = self.factory.get('/')
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quarantined')

    def test_print_post(self):
        """
        Test print post
        """
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)

        result_form = create_result_form(form_state=FormState.QUALITY_CONTROL)
        view = views.PrintView.as_view()
        data = {
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = data
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/quality-control/success', response['location'])

        result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_print_cover_get_with_no_print_cover_in_quality_control(self):
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        tally.print_cover_in_quality_control = False
        tally.save()
        result_form = create_result_form(form_state=FormState.QUALITY_CONTROL,
                                         tally=tally)
        view = views.PrintView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/quality-control/success', response['location'])

        result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_confirmation_get(self):
        """
        Test confirmation get
        """
        result_form = create_result_form(tally=self.tally,
                                         form_state=FormState.ARCHIVED)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.ConfirmationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Archiving')
        self.assertContains(
            response,
            reverse('quality-control', kwargs={'tally_id': self.tally.pk}))
        self.assertEqual(request.session.get('result_form'), None)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor,
                         False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_quality_control_post_invalid_state(self):
        """
        Test quality control view post with a form not in QC state.
        """
        barcode = '123456789'
        create_result_form(barcode,
                           tally=self.tally,
                           form_state=FormState.DATA_ENTRY_1)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlView.as_view()
        data = {
            'barcode': barcode,
            'barcode_copy': barcode,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            str('Form not in QUALITY_CONTROL or ARCHIVING.'
                '  Return form to Data Entry 1')
        )

    def test_quality_control_post_invalid_barcode(self):
        """
        Test quality control view post with an invalid barcode.
        """
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlView.as_view()
        data = {
            'barcode': '1234',
            'barcode_copy': '1234',
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Barcode does not exist.')

    def test_dashboard_get_invalid_state(self):
        """
        Test dashboard get with form in session not in QC state.
        """
        barcode = '123456789'
        result_form = create_result_form(barcode,
                                         tally=self.tally,
                                         form_state=FormState.DATA_ENTRY_1)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        with self.assertRaises(SuspiciousOperation):
            view(request, tally_id=self.tally.pk)

    def test_dashboard_post_suspicious_operation(self):
        """
        Test dashboard post raises SuspiciousOperation with missing data.
        """
        barcode = '123456789'
        result_form = create_result_form(barcode,
                                         tally=self.tally,
                                         form_state=FormState.QUALITY_CONTROL)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = { # Missing correct/incorrect/abort
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        with self.assertRaises(SuspiciousOperation):
            view(request, tally_id=self.tally.pk)

    def test_print_post_audit_state(self):
        """
        Test print post sets state to AUDIT if audit exists.
        """
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        result_form = create_result_form(form_state=FormState.QUALITY_CONTROL,
                                         tally=self.tally)
        # Create an audit associated with the result form
        create_audit(result_form, self.user)
        result_form.save()

        view = views.PrintView.as_view()
        data = {
            'result_form': result_form.pk,
            'tally_id': self.tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/quality-control/success', response['location'])

        result_form.reload()
        self.assertEqual(result_form.form_state, FormState.AUDIT)
        self.assertIsNotNone(result_form.audit)

    def test_confirmation_get_audit_state(self):
        """
        Test confirmation get for a form that moved to AUDIT state.
        """
        result_form = create_result_form(tally=self.tally,
                                         form_state=FormState.AUDIT)
        create_audit(result_form, self.user)
        ResultFormStats.objects.create(
            user=self.user, result_form=result_form, processing_time=10)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.ConfirmationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Audit')
        self.assertContains(
            response,
            reverse('quality-control', kwargs={'tally_id': self.tally.pk}))
        self.assertEqual(request.session.get('result_form'), None)

    def test_confirm_form_reset_view_post_invalid_data(self):
        """
        Test confirm form reset view post with invalid data (missing reason).
        """
        barcode = '123456789'
        ballot = create_ballot(self.tally, available_for_release=True)
        create_result_form(barcode,
                           tally=self.tally,
                           ballot=ballot,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.ConfirmFormResetView.as_view()
        data = {} # Missing 'reject_reason'
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        request.session['encoded_result_form_qa_control_start_time'] =\
            self.encoded_result_form_qa_control_start_time
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        result_form.reload()
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertTrue(quality_control.active)
        self.assertEqual(result_form.form_state, FormState.QUALITY_CONTROL)
        self.assertIsNotNone(request.session.get('result_form'))
