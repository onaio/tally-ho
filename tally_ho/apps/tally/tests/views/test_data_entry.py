from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder, json
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.views import data_entry as views
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase,
    center_data,
    create_candidate,
    create_center,
    create_result_form,
    create_station,
    create_tally,
    result_form_data,
    result_form_data_blank,
)


class TestDataEntry(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self.encoded_result_form_data_entry_start_time = json.loads(
            json.dumps(timezone.now(), cls=DjangoJSONEncoder)
        )

    def _common_view_tests(self, view):
        if not hasattr(self, "user"):
            self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        request = self.factory.get("/")
        request.session = {}
        request.session["encoded_result_form_data_entry_start_time"] = (
            self.encoded_result_form_data_entry_start_time
        )
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/accounts/login/?next=/", response["location"])
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request, tally_id=tally.pk)
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        response = view(request, tally_id=tally.pk)
        response.render()
        self.assertIn(b"/accounts/logout/", response.content)
        return response

    def _post_enter_results(self, result_form):
        view = views.EnterResultsView.as_view()
        data = result_form_data(result_form)
        self.request = self.factory.post("/", data=data)
        self.request.user = self.user
        self.request.session = {"result_form": result_form.pk}
        return view(self.request, tally_id=result_form.tally.pk)

    def test_data_entry_view(self):
        response = self._common_view_tests(views.DataEntryView.as_view())
        self.assertContains(response, "Data Entry")
        self.assertIn(b'<form id="result_form"', response.content)

    def test_center_detail_center_number_length(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.CenterDetailsView.as_view()
        data = {"center_number": "1234"}
        session = {"result_form": result_form.pk}
        data.update(session)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = session
        response = view(request, tally_id=tally.pk)

        self.assertContains(
            response, "Ensure this value has at least 5 characters"
        )

    def test_center_detail_center_not_equal(self):
        self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.CenterDetailsView.as_view()
        data = center_data("12345", "12346", tally_id=tally.pk)
        session = {"result_form": result_form.pk}
        data.update(session)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = session
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Center Numbers do not match")

    def test_center_detail_center_alpha_numeric(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.CenterDetailsView.as_view()
        data = center_data("12345", "12346", tally_id=tally.pk)
        data["center_number"] = "abcde"
        data["center_number_copy"] = "abcde"
        session = {"result_form": result_form.pk}
        data.update(session)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = session
        response = view(request, tally_id=tally.pk)
        self.assertContains(
            response, "Expecting only numbers for center number"
        )

    def test_center_detail_invalid_center(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        other_code = "21345"
        station_number = 1
        center = create_center(code, tally=tally)
        other_center = create_center(other_code, tally=tally)
        create_station(center)
        create_station(other_center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.CenterDetailsView.as_view()
        session = {"result_form": result_form.pk}
        data = center_data(
            other_code, station_number=station_number, tally_id=tally.pk
        )
        data.update(session)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = session
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertContains(
            response, "Center and station numbers do not match"
        )

    def test_center_detail_no_station(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.CenterDetailsView.as_view()
        session = {"result_form": result_form.pk}
        data = center_data(code, tally_id=tally.pk)
        data.update(session)
        data.update({"station_number": 3, "station_number_copy": 3})
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = session
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid Station Number for this Center")

    def test_center_detail_redirects_to_enter_results(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.CenterDetailsView.as_view()
        result_form_data = {"result_form": result_form.pk}
        data = center_data(
            code, station_number=station_number, tally_id=tally.pk
        )
        data.update(result_form_data)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = result_form_data
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("data-entry/enter-results", response["location"])

    def test_center_detail_validates_clerk(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_2,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.CenterDetailsView.as_view()
        result_form_data = {"result_form": result_form.pk}
        data = center_data(
            code, station_number=station_number, tally_id=tally.pk
        )
        data.update(result_form_data)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = result_form_data
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b"Data Entry 2", response.content)

    def test_enter_results_has_candidates(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally)
        station = create_station(center)
        result_form = create_result_form(
            center=center,
            form_state=FormState.DATA_ENTRY_1,
            station_number=station.station_number,
            tally=tally,
        )
        ballot = result_form.ballot
        candidate_name = "candidate name"
        create_candidate(ballot, candidate_name)

        view = views.EnterResultsView.as_view()
        data = center_data(code, tally_id=tally.pk)
        request = self.factory.get("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, candidate_name)

    def test_enter_results_invalid(self):
        self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1, tally=tally
        )
        ballot = result_form.ballot
        candidate_name = "candidate name"
        create_candidate(ballot, candidate_name)

        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        view = views.EnterResultsView.as_view()
        data = result_form_data_blank(result_form)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("data-entry", response["location"])
        self.assertEqual(
            request.session.get("clearance_error"),
            str(
                "Form rejected: All candidate votes "
                "are blank or zero, or reconciliation form "
                "is invalid."
            ),
        )

        # Verify Clearance record was created
        from tally_ho.apps.tally.models.clearance import Clearance
        clearance = Clearance.objects.get(result_form=result_form)
        self.assertEqual(clearance.user, self.user.userprofile)

    def test_enter_results_success_data_entry_one(self):
        self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally)
        station = create_station(center)
        result_form = create_result_form(
            center=center,
            form_state=FormState.DATA_ENTRY_1,
            station_number=station.station_number,
            tally=tally,
        )
        ballot = result_form.ballot
        candidate_name = "candidate name 1"
        create_candidate(ballot, candidate_name)
        candidate_name = "candidate name 2"
        create_candidate(ballot, candidate_name)

        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)

        response = self._post_enter_results(result_form)

        self.assertEqual(response.status_code, 302)
        self.assertIn("data-entry", response["location"])
        result_form.reload()
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_2)

        reconciliation_forms = result_form.reconciliationform_set.all()
        self.assertEqual(len(reconciliation_forms), 1)
        self.assertEqual(
            reconciliation_forms[0].entry_version, EntryVersion.DATA_ENTRY_1
        )

        results = result_form.results.all()
        self.assertEqual(len(results), 2)

        votes = [4, 1]
        for i, result in enumerate(results):
            self.assertEqual(result.entry_version, EntryVersion.DATA_ENTRY_1)
            self.assertEqual(result.user, self.user)
            self.assertEqual(result.votes, votes[i])

    def test_enter_results_success_data_entry_two(self):
        self._create_and_login_user()
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally)
        station = create_station(center)
        result_form = create_result_form(
            center=center,
            form_state=FormState.DATA_ENTRY_2,
            station_number=station.station_number,
            tally=tally,
        )
        ballot = result_form.ballot
        candidate_name = "candidate name 1"
        create_candidate(ballot, candidate_name)
        candidate_name = "candidate name 2"
        create_candidate(ballot, candidate_name)

        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)

        response = self._post_enter_results(result_form)

        self.assertEqual(response.status_code, 302)
        self.assertIn("data-entry", response["location"])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state, FormState.CORRECTION)

        reconciliation_forms = updated_result_form.reconciliationform_set.all()
        self.assertEqual(len(reconciliation_forms), 1)

        self.assertEqual(
            reconciliation_forms[0].entry_version, EntryVersion.DATA_ENTRY_2
        )

        results = updated_result_form.results.all()
        self.assertEqual(len(results), 2)

        votes = [4, 1]
        for i, result in enumerate(results):
            self.assertEqual(result.entry_version, EntryVersion.DATA_ENTRY_2)
            self.assertEqual(result.user, self.user)
            self.assertEqual(result.votes, votes[i])

    def test_enter_results_success_data_entry(self):
        self._create_and_login_user("data_entry_1")
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally)
        station = create_station(center)
        result_form = create_result_form(
            center=center,
            form_state=FormState.DATA_ENTRY_1,
            station_number=station.station_number,
            tally=tally,
        )
        ballot = result_form.ballot
        candidate_name = "candidate name 1"
        create_candidate(ballot, candidate_name)
        candidate_name = "candidate name 2"
        create_candidate(ballot, candidate_name)

        view = views.EnterResultsView.as_view()
        data = result_form_data(result_form)
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("data-entry", response["location"])
        result_form.refresh_from_db()
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_2)

        data_entry_1 = self.user

        self._create_and_login_user("data_entry_2")
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)
        tally.users.add(self.user)
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("data-entry", response["location"])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state, FormState.CORRECTION)
        results = updated_result_form.results.filter(
            entry_version=EntryVersion.DATA_ENTRY_2
        )
        self.assertTrue(results.count() > 0)
        self.assertEqual(results.all()[0].user, self.user)
        results = updated_result_form.results.filter(
            entry_version=EntryVersion.DATA_ENTRY_2
        )
        self.assertTrue(results.count() > 0)

        for result in results:
            self.assertEqual(result.user, self.user)
            self.assertNotEqual(result.user, data_entry_1)

    def test_confirmation_get(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_2, tally=tally
        )
        view = views.ConfirmationView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        request.session["encoded_result_form_data_entry_start_time"] = (
            self.encoded_result_form_data_entry_start_time
        )
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(request.session.get("result_form"))
        self.assertContains(response, "Data Entry 2")
        self.assertContains(
            response, reverse("data-entry", kwargs={"tally_id": tally.pk})
        )

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_confirmation_get_corrections(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.CORRECTION, tally=tally
        )
        view = views.ConfirmationView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        request.session["encoded_result_form_data_entry_start_time"] = (
            self.encoded_result_form_data_entry_start_time
        )
        response = view(request, tally_id=tally.pk)
        self.assertIsNone(request.session.get("result_form"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Corrections")
        self.assertContains(
            response, reverse("data-entry", kwargs={"tally_id": tally.pk})
        )

        result_form_stat = ResultFormStats.objects.get(user=self.user)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)
