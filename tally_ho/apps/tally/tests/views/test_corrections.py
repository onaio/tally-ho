from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.serializers.json import DjangoJSONEncoder, json
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.views import corrections as views
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_candidate,
    create_center,
    create_electrol_race,
    create_recon_forms,
    create_reconciliation_form,
    create_result_form,
    create_result_form_stats,
    create_station,
    create_tally,
)


def create_results(result_form, vote1=1, vote2=1, num=1):
    code = "12345"
    center = create_center(code)
    create_station(center)
    ballot = result_form.ballot
    candidate_name = "candidate name"
    candidate = create_candidate(ballot, candidate_name)

    for i in range(num):
        Result.objects.create(
            candidate=candidate,
            result_form=result_form,
            entry_version=EntryVersion.DATA_ENTRY_1,
            votes=vote1,
        )

        if vote2:
            Result.objects.create(
                candidate=candidate,
                result_form=result_form,
                entry_version=EntryVersion.DATA_ENTRY_2,
                votes=vote2,
            )


class TestCorrections(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.encoded_result_form_corrections_start_time = json.loads(
            json.dumps(timezone.now(), cls=DjangoJSONEncoder)
        )
        electrol_race_data = electrol_races[0]
        self.electrol_race = create_electrol_race(
            self.tally, **electrol_race_data
        )

    def _common_view_tests(self, view, session={}):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/accounts/login/?next=/", response["location"])
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        request.session = session
        response = view(request, tally_id=self.tally.pk)
        response.render()
        self.assertIn(b"/accounts/logout/", response.content)
        return response

    def test_corrections_page(self):
        response = self._common_view_tests(views.CorrectionView.as_view())
        response.render()
        self.assertIn(b"Correction", response.content)
        self.assertIn(b'<form id="result_form"', response.content)

    def test_corrections_barcode_not_equal(self):
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {
            "barcode": "123453789",
            "barcode_copy": "123456789",
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", data=barcode_data)
        request.user = self.user
        request.session = {}
        request.session["encoded_result_form_corrections_start_time"] = (
            self.encoded_result_form_corrections_start_time
        )
        response = view(request, tally_id=self.tally.pk)
        self.assertContains(response, "Barcodes do not match")

    def test_corrections_barcode_does_not_exist(self):
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {
            "barcode": "123456789",
            "barcode_copy": "123456789",
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", data=barcode_data)
        request.user = self.user
        request.session = {}
        request.session["encoded_result_form_corrections_start_time"] = (
            self.encoded_result_form_corrections_start_time
        )
        response = view(request, tally_id=self.tally.pk)
        self.assertContains(response, "Barcode does not exist")

    def test_corrections_redirects_to_corrections_match(self):
        barcode = "123456789"
        result_form = create_result_form(
            form_state=FormState.CORRECTION, tally=self.tally
        )
        create_results(result_form, vote1=1, vote2=1)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {
            "barcode": barcode,
            "barcode_copy": barcode,
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", data=barcode_data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("corrections/match", response["location"])

    def test_corrections_redirects_to_corrections_required(self):
        barcode = "123456789"
        result_form = create_result_form(
            form_state=FormState.CORRECTION, tally=self.tally
        )
        create_results(result_form, vote1=1, vote2=3)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {
            "barcode": barcode,
            "barcode_copy": barcode,
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", data=barcode_data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("corrections/required", response["location"])

    def test_corrections_match_page(self):
        code = "12345"
        center = create_center(code)
        station = create_station(center)
        result_form = create_result_form(
            center=center,
            form_state=FormState.CORRECTION,
            station_number=station.station_number,
            tally=self.tally,
        )
        session = {"result_form": result_form.pk}
        response = self._common_view_tests(
            views.CorrectionMatchView.as_view(), session=session
        )
        string_matches = [
            "Corrections",
            "Election Level:",
            "Sub Race Type:",
            "Form Entries Match",
            "Pass to Quality Control",
            '<input type="hidden" '
            f'name="result_form" value="{result_form.pk}">',
        ]
        for check_str in string_matches:
            self.assertContains(response, check_str)

    def test_corrections_match_pass_to_quality_control(self):
        view = views.CorrectionMatchView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION, tally=self.tally
        )
        create_recon_forms(result_form, self.user)
        create_results(result_form, vote1=3, vote2=3)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        data = {
            "result_form": result_form.pk,
            "pass_to_quality_control": "true",
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", data=data)
        request.session = session
        request.session["encoded_result_form_corrections_start_time"] = (
            self.encoded_result_form_corrections_start_time
        )
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 3
        )
        self.assertEqual(
            Result.objects.filter(
                result_form=result_form, entry_version=EntryVersion.FINAL
            ).count(),
            1,
        )
        self.assertEqual(
            ReconciliationForm.objects.filter(
                active=True,
                result_form=result_form,
                entry_version=EntryVersion.FINAL,
            ).count(),
            1,
        )
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.QUALITY_CONTROL
        )

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_corrections_num_results_anomaly_reset_to_data_entry_one(self):
        barcode = "123456789"
        view = views.CorrectionMatchView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION, tally=self.tally
        )
        create_recon_forms(result_form, self.user)
        create_results(result_form, vote1=3, vote2=3)
        create_results(result_form, vote1=3, vote2=None)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 3
        )

        view = views.CorrectionView.as_view()
        barcode_data = {
            "barcode": barcode,
            "barcode_copy": barcode,
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", data=barcode_data)
        request.user = self.user
        request.session = {}
        with self.assertRaises(SuspiciousOperation):
            view(request, tally_id=self.tally.pk)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.DATA_ENTRY_1
        )

    def test_corrections_post_with_note_corrections(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        create_recon_forms(
            result_form, self.user, de1_notes="", de2_notes="100"
        )

        data_entry_2_user = self._create_user("data_entry_2", "password")
        self._add_user_to_group(data_entry_2_user, groups.DATA_ENTRY_2_CLERK)

        start_time = timezone.now()
        minutes = 65.5
        end_time = start_time + timezone.timedelta(minutes=minutes)

        form_processing_time_in_seconds = (
            end_time - start_time
        ).total_seconds()

        result_form_stat = create_result_form_stats(
            processing_time=form_processing_time_in_seconds,
            user=data_entry_2_user,
            result_form=result_form,
        )

        create_results(result_form, vote1=2, vote2=2)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        post_data = {
            "notes": "100",
            "result_form": result_form.pk,
            "submit_corrections": "submit corrections",
        }
        request = self.factory.post("/", post_data)
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.QUALITY_CONTROL
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("corrections/success", response["location"])

        result_form_stat.reload()
        self.assertEqual(result_form_stat.data_entry_errors, 1)

    def test_corrections_post_with_blank_note_corrections(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        create_recon_forms(
            result_form, self.user, de1_notes="", de2_notes="100"
        )

        data_entry_2_user = self._create_user("data_entry_2", "password")
        self._add_user_to_group(data_entry_2_user, groups.DATA_ENTRY_2_CLERK)

        start_time = timezone.now()
        minutes = 65.5
        end_time = start_time + timezone.timedelta(minutes=minutes)

        form_processing_time_in_seconds = (
            end_time - start_time
        ).total_seconds()

        result_form_stat = create_result_form_stats(
            processing_time=form_processing_time_in_seconds,
            user=data_entry_2_user,
            result_form=result_form,
        )

        create_results(result_form, vote1=2, vote2=2)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        post_data = {
            "notes": "",
            "result_form": result_form.pk,
            "submit_corrections": "submit corrections",
        }
        request = self.factory.post("/", post_data)
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.QUALITY_CONTROL
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("corrections/success", response["location"])

        result_form_stat.reload()
        self.assertEqual(result_form_stat.data_entry_errors, 1)

    def tespt_corrections_post_with_corrections(self):
        view = views.CorrectionRequiredView.as_view()
        prefix = str(
            f"{self.electrol_race.election_level.lower()}"
            f"_{self.electrol_race.ballot_name.lower()}"
        )
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        data_entry_2_user = self._create_user("data_entry_2", "password")
        self._add_user_to_group(data_entry_2_user, groups.DATA_ENTRY_2_CLERK)

        start_time = timezone.now()
        minutes = 65.5
        end_time = start_time + timezone.timedelta(minutes=minutes)

        form_processing_time_in_seconds = (
            end_time - start_time
        ).total_seconds()

        result_form_stat = create_result_form_stats(
            processing_time=form_processing_time_in_seconds,
            user=data_entry_2_user,
            result_form=result_form,
        )

        create_results(result_form, vote1=2, vote2=3)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        candidate_pk = result_form.results.all()[0].candidate.pk
        post_data = {
            f"candidate_{prefix}_{candidate_pk}": 2,
            "result_form": result_form.pk,
            "submit_corrections": "submit corrections",
        }
        request = self.factory.post("/", post_data)
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.QUALITY_CONTROL
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("corrections/success", response["location"])

        result_form_stat.reload()
        self.assertEqual(result_form_stat.data_entry_errors, 1)

    def test_corrections_post_with_mis_matched_vts_nt_equal_corrections(self):
        code = "12345"
        center = create_center(code)
        station = create_station(center)
        view = views.CorrectionRequiredView.as_view()
        prefix = str(
            f"{self.electrol_race.election_level.lower()}"
            f"_{self.electrol_race.ballot_name.lower()}"
        )
        result_form = create_result_form(
            center=center,
            form_state=FormState.CORRECTION,
            station_number=station.station_number,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        create_recon_forms(result_form, self.user)
        create_results(result_form, vote1=2, vote2=3, num=2)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 4
        )
        session = {"result_form": result_form.pk}
        candidate_pk = result_form.results.all()[0].candidate.pk
        post_data = {
            f"candidate_{prefix}_{candidate_pk}": 2,
            "result_form": result_form.pk,
            "submit_corrections": "submit corrections",
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", post_data)
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state, FormState.CORRECTION)
        response.render()
        self.assertIn(
            b"Please select correct results for all mis-matched votes.",
            response.content,
        )
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 4
        )

    def test_corrections_twice(self):
        """
        Checks that results when passed through corrections, and sent to
        Quality Control and rejected  in QA then new corrections matching
        does not create more than one record of active results.
        """
        view = views.CorrectionMatchView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION, tally=self.tally
        )
        create_recon_forms(result_form, self.user)
        create_results(result_form, vote1=3, vote2=3)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        data = {
            "result_form": result_form.pk,
            "pass_to_quality_control": "true",
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", data=data)
        request.session = session
        request.session["encoded_result_form_corrections_start_time"] = (
            self.encoded_result_form_corrections_start_time
        )
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        result_form_stat = ResultFormStats.objects.get(result_form=result_form)
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 3
        )
        self.assertEqual(
            Result.objects.filter(
                result_form=result_form, entry_version=EntryVersion.FINAL
            ).count(),
            1,
        )
        self.assertEqual(
            ReconciliationForm.objects.filter(
                active=True,
                result_form=result_form,
                entry_version=EntryVersion.FINAL,
            ).count(),
            1,
        )
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.QUALITY_CONTROL
        )

        # reject result in QA
        updated_result_form.reject()

        # reset form to corrections
        updated_result_form.form_state = FormState.DATA_ENTRY_2
        updated_result_form.save()
        updated_result_form.form_state = FormState.CORRECTION
        updated_result_form.save()

        # none of the results is active
        self.assertEqual(
            Result.objects.filter(
                result_form=result_form, active=True
            ).count(),
            0,
        )
        self.assertEqual(
            ReconciliationForm.objects.filter(
                active=True,
                result_form=result_form,
                entry_version=EntryVersion.FINAL,
            ).count(),
            0,
        )

        # create new results
        create_recon_forms(result_form, self.user)
        create_results(updated_result_form, vote1=2, vote2=2)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 5
        )
        self.assertEqual(
            Result.objects.filter(
                result_form=result_form, active=True
            ).count(),
            2,
        )

        request.session = {"result_form": result_form.pk}
        request.session["encoded_result_form_corrections_start_time"] = (
            self.encoded_result_form_corrections_start_time
        )
        # pass to quality control
        response = view(request, tally_id=self.tally.pk)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.QUALITY_CONTROL
        )

        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 6
        )
        self.assertEqual(
            Result.objects.filter(
                result_form=result_form, active=True
            ).count(),
            3,
        )
        self.assertEqual(
            ReconciliationForm.objects.filter(
                active=True,
                result_form=result_form,
                entry_version=EntryVersion.FINAL,
            ).count(),
            1,
        )

        result_form_stat = ResultFormStats.objects.get(
            result_form=updated_result_form
        )
        self.assertEqual(result_form_stat.approved_by_supervisor, False)
        self.assertEqual(result_form_stat.reviewed_by_supervisor, False)
        self.assertEqual(result_form_stat.user, self.user)
        self.assertEqual(result_form_stat.result_form, result_form)

    def test_corrections_post_reject(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        create_recon_forms(result_form, self.user)
        create_results(result_form, vote1=2, vote2=3)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        candidate_pk = result_form.results.all()[0].candidate.pk
        post_data = {
            f"candidate_{candidate_pk}": 2,
            "result_form": result_form.pk,
            "reject_submit": "reject",
        }
        request = self.factory.post("/", post_data)
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/corrections", response["location"])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)

        for result in updated_result_form.results.all():
            self.assertEqual(result.active, False)

        for recon in updated_result_form.reconciliationform_set.all():
            self.assertEqual(recon.active, False)

        self.assertEqual(
            updated_result_form.form_state, FormState.DATA_ENTRY_1
        )

    def test_corrections_post_abort(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        create_results(result_form, vote1=2, vote2=3)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        candidate_pk = result_form.results.all()[0].candidate.pk
        post_data = {
            f"candidate_{candidate_pk}": 2,
            "result_form": result_form.pk,
            "abort_submit": "reject",
            "tally_id": self.tally.pk,
        }
        request = self.factory.post("/", post_data)
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/corrections", response["location"])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)

        for result in updated_result_form.results.all():
            self.assertNotEqual(result.entry_version, EntryVersion.FINAL)

        self.assertEqual(updated_result_form.form_state, FormState.CORRECTION)

    def test_recon_get(self):
        view = views.CorrectionRequiredView.as_view()
        center = create_center()
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            center=center,
            electrol_race=self.electrol_race,
        )
        create_results(result_form, vote1=2, vote2=3)
        create_recon_forms(result_form, self.user)

        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        request = self.factory.get("/")
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b"Reconciliation", response.content)

    def test_recon_get_double_entry_recon_form(self):
        view = views.CorrectionRequiredView.as_view()
        center = create_center()
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            center=center,
            electrol_race=self.electrol_race,
        )
        create_results(result_form, vote1=2, vote2=3)
        create_recon_forms(result_form, self.user)
        create_recon_forms(result_form, self.user)

        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2
        )
        session = {"result_form": result_form.pk}
        request = self.factory.get("/")
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b"Reconciliation", response.content)

    def test_recon_post(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(
            form_state=FormState.CORRECTION,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        data_entry_1_user = self._create_user("data_entry_1", "password")
        self._add_user_to_group(data_entry_1_user, groups.DATA_ENTRY_1_CLERK)
        data_entry_2_user = self._create_user("data_entry_2", "password")
        self._add_user_to_group(data_entry_2_user, groups.DATA_ENTRY_2_CLERK)

        start_time = timezone.now()
        minutes = 65.5
        end_time = start_time + timezone.timedelta(minutes=minutes)

        form_processing_time_in_seconds = (
            end_time - start_time
        ).total_seconds()

        result_form_stat_de_1 = create_result_form_stats(
            processing_time=form_processing_time_in_seconds,
            user=data_entry_1_user,
            result_form=result_form,
        )
        result_form_stat_de_2 = create_result_form_stats(
            processing_time=form_processing_time_in_seconds,
            user=data_entry_2_user,
            result_form=result_form,
        )

        create_results(result_form, vote1=2, vote2=2)

        sorted_counted_val = 3
        recon1 = create_reconciliation_form(result_form, self.user)
        recon1.entry_version = EntryVersion.DATA_ENTRY_1
        recon1.save()

        recon2 = create_reconciliation_form(
            result_form,
            self.user,
            number_sorted_and_counted=sorted_counted_val,
        )
        recon2.entry_version = EntryVersion.DATA_ENTRY_2
        recon2.save()

        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            ReconciliationForm.objects.filter(result_form=result_form).count(),
            2,
        )

        session = {"result_form": result_form.pk}
        data = {
            "submit_corrections": 1,
            "number_sorted_and_counted": sorted_counted_val,
            "tally_id": self.tally.pk,
        }
        data.update(session)
        request = self.factory.post("/", data=data)
        request.session = session
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        final_form = ReconciliationForm.objects.filter(
            result_form=result_form, entry_version=EntryVersion.FINAL
        )[0]

        self.assertEqual(
            final_form.number_sorted_and_counted, sorted_counted_val
        )
        self.assertEqual(final_form.result_form, result_form)
        self.assertEqual(final_form.entry_version, EntryVersion.FINAL)
        self.assertEqual(final_form.user, self.user)
        self.assertEqual(response.status_code, 302)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(
            updated_result_form.form_state, FormState.QUALITY_CONTROL
        )
        self.assertIn("corrections/success", response["location"])

        result_form_stat_de_1.reload()
        result_form_stat_de_2.reload()
        self.assertEqual(result_form_stat_de_1.data_entry_errors, 1)
        self.assertEqual(result_form_stat_de_2.data_entry_errors, 0)

    def test_confirmation_get(self):
        code = "12345"
        center = create_center(code)
        station = create_station(center)
        result_form = create_result_form(
            center=center,
            form_state=FormState.QUALITY_CONTROL,
            station_number=station.station_number,
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.ConfirmationView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        request.session["encoded_result_form_corrections_start_time"] = (
            self.encoded_result_form_corrections_start_time
        )
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(request.session.get("result_form"))
        self.assertContains(response, "Quality Control")
        self.assertContains(
            response,
            reverse("corrections", kwargs={"tally_id": self.tally.pk}),
        )
