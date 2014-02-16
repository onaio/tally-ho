from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.template import Template, Context
from django.test import RequestFactory

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.views import clearance as views
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_ballot, create_clearance,\
    create_result_form, TestBase


class TestClearance(TestBase):
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
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_dashboard_get(self):
        response = self._common_view_tests(
            views.DashboardView.as_view())
        self.assertContains(response, 'Clearance')

    def test_dashboard_get_supervisor(self):
        username = 'alice'
        self._create_and_login_user(username=username)
        result_form = create_result_form(form_state=FormState.CLEARANCE,
                                         station_number=42)
        create_clearance(result_form, self.user, reviewed_team=True)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        request = self.factory.get('/')
        request.user = self.user
        view = views.DashboardView.as_view()
        response = view(request)

        self.assertContains(response, 'Clearance')
        self.assertContains(response, username)
        self.assertContains(response, '42')

    def test_dashboard_get_forms(self):
        create_result_form(form_state=FormState.CLEARANCE,
                           station_number=42)
        response = self._common_view_tests(
            views.DashboardView.as_view())

        self.assertContains(response, 'Clearance')
        self.assertContains(response, '42')

    def test_dashboard_post(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.DashboardView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('clearance/review',
                      response['location'])

    def test_review_get(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forward to Supervisor')

    def test_review_get_supervisor(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)

        view = views.ReviewView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Implement Recommendation')
        self.assertContains(response, 'Return to Clearance Team')

    def test_review_post_invalid(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_review_post(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        clearance = result_form.clearance
        self.assertEqual(clearance.user, self.user)
        self.assertNotEqual(clearance.date_team_modified, None)
        self.assertEqual(clearance.reviewed_team, False)
        self.assertEqual(clearance.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_forward(self):
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'forward': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        clearance = result_form.clearance
        self.assertEqual(clearance.user, self.user)
        self.assertEqual(clearance.reviewed_team, True)
        self.assertEqual(clearance.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_supervisor(self):
        # save clearance as clerk
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        clearance = result_form.clearance
        self.assertEqual(clearance.supervisor, self.user)
        self.assertNotEqual(clearance.date_supervisor_modified, None)
        self.assertNotEqual(clearance.date_team_modified, None)
        self.assertEqual(clearance.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)

    def test_review_post_supervisor_return(self):
        # save clearance as clerk
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        # save as supervisor
        self._create_and_login_user(username='alice')
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'return': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        clearance = result_form.clearance
        self.assertEqual(clearance.supervisor, self.user)
        self.assertEqual(clearance.action_prior_to_recommendation, 1)
        self.assertEqual(clearance.reviewed_team, False)
        self.assertEqual(response.status_code, 302)

    def test_review_post_supervisor_implement(self):
        # save clearance as clerk
        result_form = create_result_form(form_state=FormState.CLEARANCE)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

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
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)

        view = views.ReviewView.as_view()
        data = {'result_form': result_form.pk,
                'action_prior_to_recommendation': 1,
                'resolution_recommendation': 2,
                'implement': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = data
        response = view(request)

        clearance = result_form.clearances.all()[0]
        result_form.reload()

        self.assertEqual(clearance.supervisor, self.user)
        self.assertEqual(clearance.active, False)
        self.assertEqual(clearance.reviewed_supervisor, True)
        self.assertEqual(clearance.reviewed_team, True)
        self.assertEqual(clearance.action_prior_to_recommendation, 1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_new_form_get_with_form(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        result_form = create_result_form(form_state=FormState.UNSUBMITTED)

        view = views.NewFormView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context_data['result_form'].barcode),
                         result_form.barcode)

    def test_new_form_get(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        create_result_form(form_state=FormState.UNSUBMITTED)

        view = views.NewFormView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request)
        pk = request.session['result_form']

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(pk)

        result_form = ResultForm.objects.get(pk=pk)
        self.assertIsNotNone(result_form.barcode)
        self.assertEqual(result_form.form_state, FormState.CLEARANCE)

    def test_new_form_post(self):
        # save clearance as clerk
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            force_ballot=False,
            gender=None)
        ballot = create_ballot()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.NewFormView.as_view()
        data = {'result_form': result_form.pk,
                'gender': [u'0'],
                'ballot': [ballot.pk]}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(result_form.created_user, self.request.user)
        self.assertEqual(result_form.gender, 0)
        self.assertIn('clearance', response['location'])

    def test_new_form_post_invalid(self):
        # save clearance as clerk
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            force_ballot=False,
            gender=None)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.NewFormView.as_view()
        data = {'result_form': result_form.pk,
                'gender': [u'0']}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        result_form.reload()

        pk = request.session['result_form']

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(pk)

        result_form = ResultForm.objects.get(pk=pk)
        self.assertIsNotNone(result_form.barcode)
        self.assertEqual(result_form.form_state, FormState.CLEARANCE)

    def test_print_cover_supervisor(self):
        username = 'alice'
        self._create_and_login_user(username=username)
        result_form = create_result_form(form_state=FormState.CLEARANCE,
                                         station_number=42)
        create_clearance(result_form, self.user, reviewed_team=True)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        view = views.PrintCoverView.as_view()
        response = view(request)

        self.assertContains(response, 'Clearance Case')
        self.assertContains(response, '42')

    def test_print_cover_clerk(self):
        username = 'alice'
        self._create_and_login_user(username=username)
        result_form = create_result_form(form_state=FormState.CLEARANCE,
                                         station_number=42)
        create_clearance(result_form, self.user, reviewed_team=True)
        date_str = Template("{{k}}").render(
            Context({'k': result_form.clearance.date_team_modified}))
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        view = views.PrintCoverView.as_view()
        response = view(request)

        self.assertContains(response, 'Clearance Case')
        self.assertContains(response, '42')
        self.assertContains(response, date_str)
