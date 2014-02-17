from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.test import RequestFactory

from libya_tally.apps.tally.views import quality_control as views
from libya_tally.apps.tally.models.quality_control import QualityControl
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_candidates,\
    create_reconciliation_form, create_recon_forms, create_result_form,\
    TestBase


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
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/accounts/login/?next=/', response['location'])
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
        data = {'result_form': result_form.pk,
                'abort': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        quality_control = result_form.qualitycontrol_set.all()[0]

        self.assertEqual(quality_control.active, False)
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
        data = {'result_form': result_form.pk,
                'correct': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        result_form = ResultForm.objects.get(pk=result_form.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/success',
                      response['location'])
        self.assertEqual(result_form.form_state, FormState.ARCHIVING)

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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(result_form.gender_name))
        self.assertContains(response, 'General Results Section')
        self.assertNotContains(response, 'Reconciliation')
        self.assertContains(response, 'Abort')

    def test_reconciliation_get(self):
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        self._create_and_login_user()
        create_reconciliation_form(result_form)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reconciliation')
        self.assertContains(response, 'Total number of the sorted and counted')

    def test_reconciliation_post_correct(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {'result_form': result_form.pk, 'correct': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/success',
                      response['location'])
        quality_control = QualityControl.objects.get(
            pk=result_form.qualitycontrol.pk)
        self.assertEqual(result_form.form_state, FormState.ARCHIVING)
        self.assertTrue(quality_control.passed_reconciliation)

    def test_reconciliation_post_incorrect(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_recon_forms(result_form)
        create_candidates(result_form, self.user)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
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

        recon_forms = result_form.reconciliationform_set.all()
        self.assertTrue(len(recon_forms) > 0)

        for recon in recon_forms:
            self.assertEqual(recon.active, False)

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
        view = views.QualityControlDashboardView.as_view()
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
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(result_form.gender_name))
        self.assertContains(response, 'General')
        self.assertContains(response, name)
        self.assertContains(response, women_name)
        self.assertContains(response, str(votes))

    def test_general_post_correct(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {'result_form': result_form.pk, 'correct': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/success',
                      response['location'])
        quality_control = QualityControl.objects.get(
            pk=result_form.qualitycontrol.pk)
        self.assertEqual(result_form.form_state, FormState.ARCHIVING)
        self.assertTrue(quality_control.passed_general)

    def test_general_post_incorrect(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
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
        view = views.QualityControlDashboardView.as_view()
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
        view = views.QualityControlDashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(result_form.gender_name))
        self.assertContains(response, 'Women')
        self.assertContains(response, women_name)
        self.assertContains(response, name)
        self.assertContains(response, str(votes))

    def test_women_post_correct(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
        data = {'result_form': result_form.pk, 'correct': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertIn('quality-control/success',
                      response['location'])
        quality_control = result_form.qualitycontrol_set.all()[0]
        self.assertEqual(result_form.form_state, FormState.ARCHIVING)
        self.assertTrue(quality_control.passed_women)

    def test_women_post_incorrect(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(barcode,
                           form_state=FormState.QUALITY_CONTROL)
        result_form = ResultForm.objects.get(barcode=barcode)
        create_quality_control(result_form, self.user)
        create_candidates(result_form, self.user)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.QualityControlDashboardView.as_view()
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
        view = views.QualityControlDashboardView.as_view()
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

    def test_confirmation_get(self):
        result_form = create_result_form(form_state=FormState.ARCHIVING)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_CLERK)
        view = views.ConfirmationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Archiving')
        self.assertContains(response, reverse('quality-control-clerk'))
        self.assertEqual(request.session.get('result_form'), None)
