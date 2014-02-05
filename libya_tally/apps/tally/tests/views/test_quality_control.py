from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import quality_control as views
from libya_tally.apps.tally.models.quality_control import QualityControl
from libya_tally.apps.tally.models.reconciliation_form import\
    ReconciliationForm
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_candidates,\
    create_result_form, TestBase


def create_quality_control(result_form, user):
    return QualityControl.objects.create(result_form=result_form,
                                         user=user)


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
        self.assertEqual(result_form.qualitycontrol.user, self.user)

    def test_dashboard_abort_post(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        view = views.QualityControlDashboardView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        self.assertEqual(request.session, {})

    def test_dashboard_submit_post(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        self._create_and_login_user()
        result_form = ResultForm.objects.get(barcode=barcode)
        quality_control = create_quality_control(result_form, self.user)
        quality_control.passed_general = True
        quality_control.passed_reconciliation = True
        quality_control.passed_women = True
        quality_control.save()

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        result_form = ResultForm.objects.get(pk=result_form.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        self.assertEqual(result_form.form_state, FormState.ARCHIVING)
        self.assertEqual(request.session, {})

    def test_dashboard_get(self):
        barcode = '123456789'
        self._create_and_login_user()
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(result_form.gender_name), response.content)
        self.assertIn('Reviews Required', response.content)
        self.assertNotIn('Reconciliation', response.content)
        self.assertIn('Abort', response.content)

    def test_dashboard_get_reviewed(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        self._create_and_login_user()
        qc = create_quality_control(result_form, self.user)
        qc.passed_general = True
        qc.passed_womens = True
        qc.save()

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(result_form.gender_name), response.content)
        result_form.qualitycontrol.reviews_passed
        self.assertIn('Reviews Complete', response.content)
        self.assertIn('Submit', response.content)

    def test_reconciliation_get(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        self._create_and_login_user()
        ReconciliationForm.objects.create(
            result_form=result_form,
            ballot_number_from=1,
            ballot_number_to=1,
            number_ballots_received=1,
            number_signatures_in_vr=1,
            number_unused_ballots=1,
            number_spoiled_ballots=1,
            number_cancelled_ballots=1,
            number_ballots_outside_box=1,
            number_ballots_inside_box=1,
            number_ballots_inside_and_outside_box=1,
            number_unstamped_ballots=1,
            number_invalid_votes=1,
            number_valid_votes=1,
            number_sorted_and_counted=1)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlReconciliationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(result_form.gender_name), response.content)
        self.assertIn('Reconciliation', response.content)
        self.assertIn('Number sorted and counted', response.content)

    def test_reconciliation_post_correct(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlReconciliationView.as_view()
        data = {'result_form': result_form.pk, 'correct': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/dashboard',
                      response['location'])
        quality_control = QualityControl.objects.get(
            pk=result_form.qualitycontrol.pk)
        self.assertTrue(quality_control.passed_reconciliation, True)

    def test_reconciliation_post_incorrect(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlReconciliationView.as_view()
        data = {'result_form': result_form.pk, 'incorrect': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
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
        self.assertEqual(quality_control.passed_reconciliation, False)

    def test_reconciliation_post_abort(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlReconciliationView.as_view()
        data = {'result_form': result_form.pk, 'abort': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertEqual(quality_control.active, False)

    def test_general_get(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        self._create_and_login_user()
        name = 'the candidate name'
        women_name = 'women candidate name'
        votes = 123

        create_candidates(result_form, self.user, name, votes, women_name)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlGeneralView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(result_form.gender_name), response.content)
        self.assertIn('General', response.content)
        self.assertIn(name, response.content)
        self.assertNotIn(women_name, response.content)
        self.assertIn(str(votes), response.content)

    def test_general_post_correct(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlGeneralView.as_view()
        data = {'result_form': result_form.pk, 'correct': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/dashboard',
                      response['location'])
        quality_control = QualityControl.objects.get(
            pk=result_form.qualitycontrol.pk)
        self.assertTrue(quality_control.passed_general, True)

    def test_general_post_incorrect(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlGeneralView.as_view()
        data = {'result_form': result_form.pk, 'incorrect': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
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
        self.assertEqual(quality_control.passed_general, False)

    def test_general_post_abort(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlGeneralView.as_view()
        data = {'result_form': result_form.pk, 'abort': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertEqual(quality_control.active, False)

    def test_women_get(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        self._create_and_login_user()
        name = 'general candidate name'
        women_name = 'women candidate name'
        votes = 123

        create_candidates(result_form, self.user, name, votes, women_name)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlWomenView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(result_form.gender_name), response.content)
        self.assertIn('Women', response.content)
        self.assertIn(women_name, response.content)
        self.assertNotIn(name, response.content)
        self.assertIn(str(votes), response.content)

    def test_women_post_correct(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlWomenView.as_view()
        data = {'result_form': result_form.pk, 'correct': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/dashboard',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertTrue(quality_control.passed_women, True)

    def test_women_post_incorrect(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlWomenView.as_view()
        data = {'result_form': result_form.pk, 'incorrect': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
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
        self.assertEqual(quality_control.passed_women, False)

    def test_women_post_abort(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlWomenView.as_view()
        data = {'result_form': result_form.pk, 'abort': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/home',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertEqual(quality_control.active, False)
