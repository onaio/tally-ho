from importlib import import_module

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder, json
from django.template import Context, Template
from django.test import RequestFactory
from django.utils import timezone

from tally_ho.apps.tally.models import Center
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.views import clearance as views
from tally_ho.apps.tally.views.super_admin import CreateResultFormView
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_candidates, create_center,
                                           create_clearance,
                                           create_constituency,
                                           create_electrol_race, create_office,
                                           create_recon_forms, create_region,
                                           create_result_form, create_station,
                                           create_sub_constituency,
                                           create_tally)

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

EXPECTED_FORM_STATE_ERROR = (
    "Form not in CORRECTION or DATA_ENTRY_1 or DATA_ENTRY_2 or "
    "INTAKE or QUALITY_CONTROL or ARCHIVING or UNSUBMITTED. "
    "Return form to Clearance"
)


class TestClearance(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self.encoded_result_form_clearance_start_time = json.loads(
            json.dumps(timezone.now(), cls=DjangoJSONEncoder)
        )

    def _common_view_tests(self, view, tally=None):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/accounts/login/?next=/", response["location"])
        self._create_and_login_user()
        if not tally:
            tally = create_tally()
        tally.users.add(self.user)
        request.user = self.user
        request.session = {}
        with self.assertRaises(PermissionDenied):
            view(request, tally_id=tally.pk)
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        response = view(request, tally_id=tally.pk)
        response.render()
        self.assertIn(b"/accounts/logout/", response.content)
        return response

    def test_dashboard_get(self):
        response = self._common_view_tests(views.DashboardView.as_view())
        self.assertContains(response, "Clearance")

    def test_dashboard_get_supervisor(self):
        username = "alice"
        self._create_and_login_user(username=username)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, station_number=42, tally=tally
        )
        create_clearance(result_form, self.user, reviewed_team=True)

        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)

        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        view = views.DashboardView.as_view()
        response = view(request, tally_id=tally.pk)

        self.assertContains(response, "Clearance")
        self.assertContains(response, username)
        self.assertContains(response, "42")

    def test_dashboard_get_csv(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        create_result_form(form_state=FormState.CLEARANCE, tally=tally)
        view = views.DashboardView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk, format="csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv")

    def test_dashboard_get_forms(self):
        tally = create_tally()
        create_result_form(
            form_state=FormState.CLEARANCE, station_number=42, tally=tally
        )
        response = self._common_view_tests(
            views.DashboardView.as_view(), tally=tally
        )

        self.assertContains(response, "Clearance")
        self.assertContains(response, "42")

    def test_dashboard_post(self):
        self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )
        tally.users.add(self.user)
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.DashboardView.as_view()
        data = {
            "result_form": result_form.pk,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("clearance/review", response["location"])

    def test_review_get(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )

        view = views.ReviewView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {
            "result_form": result_form.pk,
            "tally_id": tally.pk,
        }
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forward to Supervisor")

    def test_review_get_supervisor(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )

        view = views.ReviewView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mark Form as Resolved")
        self.assertContains(response, "Return to Clearance Team")

    def test_review_post_invalid(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )

        view = views.ReviewView.as_view()
        # invalid enum value
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 9,
            "resolution_recommendation": 0,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        request.user = self.user
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.session = data
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        request.user = self.user
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.session = data
        response = view(request, tally_id=tally.pk)

        clearance = result_form.clearance
        self.assertEqual(clearance.user, self.user)
        self.assertNotEqual(clearance.date_team_modified, None)
        self.assertEqual(clearance.reviewed_team, False)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )
        self.assertEqual(response.status_code, 302)

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_forward(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "forward": 1,
            "tally_id": tally.pk,
        }

        request = self.factory.post("/", data=data)
        request.user = self.user
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.session = data
        response = view(request, tally_id=tally.pk)

        clearance = result_form.clearance
        self.assertEqual(clearance.user, self.user)
        self.assertEqual(clearance.reviewed_team, True)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )
        self.assertEqual(response.status_code, 302)

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_supervisor(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "tally_id": tally.pk,
        }

        request = self.factory.post("/", data=data)
        request.user = self.user
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username="alice")
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        request.user = self.user
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.session = data
        response = view(request, tally_id=tally.pk)

        clearance = result_form.clearance
        self.assertEqual(clearance.supervisor, self.user)
        self.assertNotEqual(clearance.date_supervisor_modified, None)
        self.assertNotEqual(clearance.date_team_modified, None)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )
        self.assertEqual(response.status_code, 302)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_supervisor_return(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username="alice")
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "return": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        clearance = result_form.clearance
        self.assertEqual(clearance.supervisor, self.user)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )
        self.assertEqual(clearance.reviewed_team, False)
        self.assertEqual(response.status_code, 302)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_supervisor_implement(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station_number = 2
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        self.assertEqual(result_form.center, center)
        self.assertEqual(result_form.station_number, station_number)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "forward": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username="alice")
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)

        # Store the current state before implementing resolution
        initial_state = result_form.form_state

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 3,  # RESET_TO_PREINTAKE
            "implement": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        clearance = result_form.clearances.all()[0]
        result_form.reload()

        self.assertEqual(clearance.supervisor, self.user)
        self.assertFalse(clearance.active)
        self.assertTrue(clearance.reviewed_supervisor)
        self.assertTrue(clearance.reviewed_team)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

        # Verify tracking fields set when implementing RESET_TO_PREINTAKE
        self.assertEqual(result_form.previous_form_state, initial_state)
        self.assertEqual(result_form.user, self.user.userprofile)

        self.assertEqual(result_form.center, center)
        self.assertEqual(result_form.station_number, station_number)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_supervisor_implement_skip_all_zero_votes_check(self):
        """Test that implementing
        RESET_TO_PREINTAKE_AND_SKIP_ALL_ZERO_VOTES_CHECK resolution sets the
        skip_all_zero_votes_check flag to True."""
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station_number = 2
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        self.assertEqual(result_form.center, center)
        self.assertEqual(result_form.station_number, station_number)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "forward": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username="alice")
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)

        # Store the current state before implementing resolution
        initial_state = result_form.form_state

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            # RESET_TO_PREINTAKE_AND_SKIP_ALL_ZERO_VOTES_CHECK
            "resolution_recommendation": 4,
            "implement": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        clearance = result_form.clearances.all()[0]
        result_form.reload()

        self.assertEqual(clearance.supervisor, self.user)
        self.assertFalse(clearance.active)
        self.assertTrue(clearance.reviewed_supervisor)
        self.assertTrue(clearance.reviewed_team)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

        # Verify tracking fields set when implementing
        # RESET_TO_PREINTAKE_AND_SKIP_ALL_ZERO_VOTES_CHECK
        self.assertEqual(result_form.previous_form_state, initial_state)
        self.assertEqual(result_form.user, self.user.userprofile)

        # Verify the skip_all_zero_votes_check flag is set to True
        self.assertTrue(result_form.skip_all_zero_votes_check)

        self.assertEqual(result_form.center, center)
        self.assertEqual(result_form.station_number, station_number)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_review_post_supervisor_implement_replacement_form(self):
        # save clearance as clerk
        self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            is_replacement=True,
            center=center,
            tally=tally,
            station_number=2,
        )
        self.assertEqual(result_form.center, center)
        self.assertEqual(result_form.station_number, 2)
        self.assertTrue(result_form.is_replacement)
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "forward": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username="alice")
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 3,
            "implement": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        clearance = result_form.clearances.all()[0]
        result_form.reload()

        self.assertEqual(clearance.supervisor, self.user)
        self.assertFalse(clearance.active)
        self.assertTrue(clearance.reviewed_supervisor)
        self.assertTrue(clearance.reviewed_team)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )

        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)
        self.assertIsNone(result_form.center)
        self.assertIsNone(result_form.station_number)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_post_implement_replacement_form_skip_all_zero_votes_check(
        self
    ):
        """Test that implementing
        RESET_TO_PREINTAKE_AND_SKIP_ALL_ZERO_VOTES_CHECK resolution on
        replacement forms sets the skip_all_zero_votes_check flag and clears
        center/station data."""
        # save clearance as clerk
        self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            is_replacement=True,
            center=center,
            tally=tally,
            station_number=2,
        )
        self.assertEqual(result_form.center, center)
        self.assertEqual(result_form.station_number, 2)
        self.assertTrue(result_form.is_replacement)
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            "resolution_recommendation": 0,
            "forward": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        # save as supervisor
        self._create_and_login_user(username="alice")
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)

        view = views.ReviewView.as_view()
        data = {
            "result_form": result_form.pk,
            "action_prior_to_recommendation": 1,
            # RESET_TO_PREINTAKE_AND_SKIP_ALL_ZERO_VOTES_CHECK
            "resolution_recommendation": 4,
            "implement": 1,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        data["encoded_result_form_clearance_start_time"] = (
            self.encoded_result_form_clearance_start_time
        )
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        clearance = result_form.clearances.all()[0]
        result_form.reload()

        self.assertEqual(clearance.supervisor, self.user)
        self.assertFalse(clearance.active)
        self.assertTrue(clearance.reviewed_supervisor)
        self.assertTrue(clearance.reviewed_team)
        self.assertEqual(
            clearance.action_prior_to_recommendation,
            ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
        )

        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)
        # Verify center and station are cleared for replacement forms
        self.assertIsNone(result_form.center)
        self.assertIsNone(result_form.station_number)
        # Verify the skip_all_zero_votes_check flag is set to True
        self.assertTrue(result_form.skip_all_zero_votes_check)

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_new_form_get_with_form(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.UNSUBMITTED, tally=tally
        )
        view = CreateResultFormView.as_view(clearance_result_form=True)
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(result_form.barcode)
        self.assertEqual(
            str(response.context_data["title"]), "Clearance: New Result Form"
        )

    def test_new_form_get(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally
        )
        view = CreateResultFormView.as_view(clearance_result_form=True)
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)

        self.assertIsNotNone(result_form.barcode)
        self.assertEqual(result_form.form_state, FormState.CLEARANCE)

    def test_new_form_post(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        office = create_office(tally=tally)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            force_ballot=False,
            tally=tally,
            gender=Gender.MALE,
        )
        ballot = create_ballot(tally=tally)
        view = CreateResultFormView.as_view(clearance_result_form=True)
        data = {
            "result_form": result_form.pk,
            "gender": ["0"],
            "ballot": [ballot.pk],
            "center": [center.pk],
            "office": [office.pk],
            "tally": tally.id,
            "station_number": station.station_number,
        }
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.id)
        result_form.reload()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result_form.gender, Gender.MALE)

    def test_new_form_post_invalid(self):
        # save clearance as clerk
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            force_ballot=False,
            tally=tally,
            gender=None,
        )
        view = CreateResultFormView.as_view(clearance_result_form=True)
        data = {
            "result_form": result_form.pk,
            "gender": ["0"],
            "tally_id": tally.id,
        }
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)
        result_form.reload()

        pk = request.session["result_form"]

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(pk)

        result_form = ResultForm.objects.get(pk=pk)
        self.assertIsNotNone(result_form.barcode)
        self.assertEqual(result_form.form_state, FormState.CLEARANCE)

    def test_print_cover_supervisor(self):
        username = "alice"
        self._create_and_login_user(username=username)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally, station_number=42
        )
        create_clearance(result_form, self.user, reviewed_team=True)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_SUPERVISOR)
        tally.users.add(self.user)
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        view = views.PrintCoverView.as_view()
        response = view(request, tally_id=tally.pk)

        self.assertContains(response, "Clearance Case")
        self.assertContains(response, "42")

    def test_print_cover_clerk(self):
        username = "alice"
        self._create_and_login_user(username=username)
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally, station_number=42
        )
        create_clearance(result_form, self.user, reviewed_team=True)
        date_str = Template("{{k}}").render(
            Context({"k": result_form.clearance.date_team_modified})
        )
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        view = views.PrintCoverView.as_view()
        response = view(request, tally_id=tally.pk)

        self.assertContains(response, "Clearance Case")
        self.assertContains(response, "42")
        self.assertContains(response, date_str)

    def test_print_cover_get_with_no_print_cover_in_clearance(self):
        username = "alice"
        self._create_and_login_user(username=username)
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        tally.print_cover_in_clearance = False
        tally.save()
        result_form = create_result_form(
            form_state=FormState.CLEARANCE, tally=tally, station_number=42
        )
        create_clearance(result_form, self.user, reviewed_team=True)
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        view = views.PrintCoverView.as_view()
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, f"/clearance/{tally.pk}/", fetch_redirect_response=False
        )
        self.assertNotIn("result_form", request.session)

    def test_create_clearance_get(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)

        view = views.CreateClearanceView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Clearance")

    def test_create_clearance_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CLEARANCE_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        barcode = 123456789
        serial_number = 0
        clearable_states = [
            FormState.CORRECTION,
            FormState.DATA_ENTRY_1,
            FormState.DATA_ENTRY_2,
            FormState.INTAKE,
            FormState.QUALITY_CONTROL,
            FormState.UNSUBMITTED,
        ]

        for form_state in clearable_states:
            result_form = create_result_form(
                form_state=form_state,
                barcode=barcode,
                tally=tally,
                serial_number=serial_number,
            )
            # Store initial state for tracking verification
            initial_state = result_form.form_state

            create_recon_forms(result_form, self.user)
            create_candidates(result_form, self.user)
            view = views.AddClearanceFormView.as_view()
            data = {
                "accept_submit": 1,
                "result_form": result_form.pk,
                "tally_id": tally.pk,
            }
            request = self.factory.post("/", data=data)
            request.user = self.user
            data["encoded_result_form_clearance_start_time"] = (
                self.encoded_result_form_clearance_start_time
            )
            request.session = data
            response = view(request, tally_id=tally.pk)
            result_form.reload()

            self.assertEqual(response.status_code, 302)
            self.assertEqual(result_form.form_state, FormState.CLEARANCE)

            # Verify tracking fields added in commit b2393aa2
            self.assertEqual(result_form.previous_form_state, initial_state)
            self.assertEqual(result_form.user, self.user.userprofile)
            # Verify reject_reason was set with descriptive text
            self.assertIsNotNone(result_form.reject_reason)
            self.assertIn(
                "Clearance case created by user", result_form.reject_reason
            )
            self.assertIn(self.user.username, result_form.reject_reason)

            self.assertIsNotNone(result_form.clearance)
            self.assertEqual(result_form.clearance.user, self.user)

            result_form_stat = ResultFormStats.objects.get(
                result_form=result_form
            )
            self.assertEqual(result_form_stat.approved_by_supervisor, False)
            self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
            self.assertEqual(result_form_stat.user, self.user)
            self.assertEqual(result_form_stat.result_form, result_form)

            for result in result_form.reconciliationform_set.all():
                self.assertFalse(result.active)

            for result in result_form.results.all():
                self.assertFalse(result.active)

            barcode = barcode + 1
            serial_number = serial_number + 1

        # unclearable
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode=barcode,
            tally=tally,
            serial_number=serial_number,
        )
        view = views.CreateClearanceView.as_view()
        data = {
            "barcode": result_form.barcode,
            "barcode_copy": result_form.barcode,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = data
        response = view(request, tally_id=tally.pk)
        result_form.reload()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_create_clearance_post_super(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        tally = create_tally()
        tally.users.add(self.user)
        barcode = 123456789
        serial_number = 0
        clearable_states = [
            FormState.ARCHIVED,
            FormState.CORRECTION,
            FormState.DATA_ENTRY_1,
            FormState.DATA_ENTRY_2,
            FormState.INTAKE,
            FormState.QUALITY_CONTROL,
            FormState.UNSUBMITTED,
        ]

        for form_state in clearable_states:
            result_form = create_result_form(
                form_state=form_state,
                barcode=barcode,
                tally=tally,
                serial_number=serial_number,
            )
            # Store initial state for tracking verification
            initial_state = result_form.form_state

            create_recon_forms(result_form, self.user)
            create_candidates(result_form, self.user)
            view = views.AddClearanceFormView.as_view()
            data = {
                "accept_submit": 1,
                "result_form": result_form.pk,
                "tally_id": tally.pk,
            }
            request = self.factory.post("/", data=data)
            request.user = self.user
            data["encoded_result_form_clearance_start_time"] = (
                self.encoded_result_form_clearance_start_time
            )
            request.session = data
            response = view(request, tally_id=tally.pk)
            result_form.reload()

            self.assertEqual(response.status_code, 302)
            self.assertEqual(result_form.form_state, FormState.CLEARANCE)

            # Verify tracking fields added in commit b2393aa2
            self.assertEqual(result_form.previous_form_state, initial_state)
            self.assertEqual(result_form.user, self.user.userprofile)
            # Verify reject_reason was set with descriptive text
            self.assertIsNotNone(result_form.reject_reason)
            self.assertIn(
                "Clearance case created by user", result_form.reject_reason
            )
            self.assertIn(self.user.username, result_form.reject_reason)

            self.assertIsNotNone(result_form.clearance)
            self.assertEqual(result_form.clearance.user, self.user)

            result_form_stat = ResultFormStats.objects.get(
                result_form=result_form
            )
            self.assertEqual(result_form_stat.approved_by_supervisor, False)
            self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
            self.assertEqual(result_form_stat.user, self.user)
            self.assertEqual(result_form_stat.result_form, result_form)

            for result in result_form.reconciliationform_set.all():
                self.assertFalse(result.active)

            for result in result_form.results.all():
                self.assertFalse(result.active)

            barcode = barcode + 1
            serial_number = serial_number + 1

    def test_check_center_details_view(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(tally, **electrol_races[0])
        ballot = create_ballot(tally, electrol_race=electrol_race)
        region = create_region(tally=tally)
        office = create_office(tally=tally, region=region)
        constituency = create_constituency(tally=tally)
        sc = create_sub_constituency(
            code=1, field_office="1", ballots=[ballot]
        )
        center, _ = Center.objects.get_or_create(
            code="1",
            mahalla="1",
            name="1",
            office=office,
            region="1",
            village="1",
            active=True,
            tally=tally,
            sub_constituency=sc,
            center_type=CenterType.GENERAL,
            constituency=constituency,
        )
        station = create_station(center=center, registrants=20, tally=tally)
        result_form = create_result_form(
            tally=tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=station.station_number,
            ballot=ballot,
        )
        view = views.CheckCenterDetailsView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.id}
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        request = self.factory.post("/")
        request.user = self.user
        request.session = {"result_form": result_form.id}
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

    def test_check_center_details_view_errors(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        tally = create_tally()
        tally.users.add(self.user)
        electrol_race = create_electrol_race(tally, **electrol_races[0])
        ballot = create_ballot(tally, electrol_race=electrol_race)
        region = create_region(tally=tally)
        office = create_office(tally=tally, region=region)
        constituency = create_constituency(tally=tally)
        sc = create_sub_constituency(
            code=1, field_office="1", ballots=[ballot]
        )
        center, _ = Center.objects.get_or_create(
            code="1",
            mahalla="1",
            name="1",
            office=office,
            region="1",
            village="1",
            active=True,
            tally=tally,
            sub_constituency=sc,
            center_type=CenterType.GENERAL,
            constituency=constituency,
        )
        station = create_station(center=center, registrants=20, tally=tally)
        result_form = create_result_form(
            tally=tally,
            # form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=station.station_number,
            ballot=ballot,
        )
        view = views.CreateClearanceView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = SessionStore()
        request.session["result_form"] = result_form.id
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

        # without post data
        request = self.factory.post("/")
        request.session = SessionStore()
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertContains(
            response,
            (
                'Tally ID: <ul class="errorlist">'
                "<li>This field is required.</li></ul>"
            ),
        )

        # with post data, missing barcode
        post_data = {"tally_id": tally.id}
        request = self.factory.post("/", data=post_data)
        request.session = SessionStore()
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertContains(response, "Barcode does not exist.")

        # with post data
        post_data = {
            "tally_id": tally.id,
            "barcode": result_form.barcode,
            "barcode_copy": result_form.barcode,
        }
        request = self.factory.post("/", data=post_data)
        request.session = SessionStore()
        request.user = self.user
        # have the form in CLEARANCE state
        result_form.form_state = FormState.CLEARANCE
        result_form.save()
        response = view(request, tally_id=tally.id)
        self.assertContains(response, EXPECTED_FORM_STATE_ERROR)
        result_form.form_state = FormState.UNSUBMITTED
        result_form.save()

        # with post data
        post_data = {
            "tally_id": tally.id,
            "barcode": result_form.barcode,
            "barcode_copy": result_form.barcode,
        }
        request = self.factory.post("/", data=post_data)
        request.session = SessionStore()
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, f"/clearance/check-center-details/{tally.id}/"
        )
