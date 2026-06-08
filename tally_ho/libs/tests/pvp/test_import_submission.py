"""Tests for the per-submission PVP import.

These tests need the database (it's the first PVP utility that writes to
Django models). Image-extraction tests use ``captureOnCommitCallbacks`` so
``transaction.on_commit`` fires inside the test wrapping transaction.
"""

import io
import os
import shutil
import tempfile
import zipfile

from django.test import TestCase, override_settings
from reversion.models import Version

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.result import Result
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.pvp.bundle import CandidateResult, ParsedSubmission
from tally_ho.libs.pvp.import_submission import import_bundle, import_submission
from tally_ho.libs.tests.test_base import (
    TestBase, create_ballot, create_center, create_electrol_race,
    create_result_form, create_station, create_tally,
)


class ImportSubmissionTestBase(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self.electrol_race = create_electrol_race(
            self.tally,
            election_level="presidential",
            ballot_name="Presidential",
        )
        self.ballot = create_ballot(
            self.tally, electrol_race=self.electrol_race, number=1,
        )
        self.center = create_center(tally=self.tally)
        self.station = create_station(
            center=self.center, tally=self.tally,
            station_number=3, registrants=300,
        )
        # Two candidates with distinct integer candidate_ids that will be
        # referenced from the parsed submission.
        self.cand1 = Candidate.objects.create(
            ballot=self.ballot, electrol_race=self.electrol_race,
            tally=self.tally, candidate_id=131301, order=1,
            full_name="Candidate One", active=True,
        )
        self.cand2 = Candidate.objects.create(
            ballot=self.ballot, electrol_race=self.electrol_race,
            tally=self.tally, candidate_id=131302, order=2,
            full_name="Candidate Two", active=True,
        )
        self.result_form = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=self.station.station_number,
            barcode="111", form_state=FormState.UNSUBMITTED,
        )
        self.bundle = PvpUploadBundle.objects.create(
            tally=self.tally, uploaded_by=self.user,
            filename="bundle.zip", mode=PvpMode.DE1_ONLY,
        )

        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def _parsed_submission(self, **overrides):
        defaults = dict(
            odk_instance_id="uuid:rf-1",
            odk_form_id="results_14065",
            barcode="111",
            ballot_number="1313",
            staff_user_name="clerk",
            candidates=(
                CandidateResult(
                    candidate_id="131301", candidate_order=1,
                    round1=10, round2=12,
                ),
                CandidateResult(
                    candidate_id="131302", candidate_order=2,
                    round1=8, round2=9,
                ),
            ),
            recon={
                "reconciliation_r1-number_ballots_received_r1": 300,
                "reconciliation_r1-number_voter_cards_r1": 120,
                "reconciliation_r1-number_valid_ballots_r1": 118,
                "reconciliation_r1-number_invalid_ballots_r1": 2,
                "reconciliation_r1-number_ballots_inside_box_r1": 120,
                "reconciliation_r2-number_ballots_received_r2": 300,
                "reconciliation_r2-number_voter_cards_r2": 121,
                "reconciliation_r2-number_valid_ballots_r2": 118,
                "reconciliation_r2-number_invalid_ballots_r2": 3,
                "reconciliation_r2-number_ballots_inside_box_r2": 121,
            },
            images={
                "clerk_signature": "sig.jpg",
                "forms_picture_1st_page": "p1.jpg",
                "forms_picture_2nd_page": None,
            },
        )
        defaults.update(overrides)
        return ParsedSubmission(**defaults)

    def _zip_with_images(self, files):
        """Build an in-memory zip with media/<name>: bytes entries."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w") as zf:
            for name, data in files.items():
                zf.writestr(f"media/{name}", data)
        buf.seek(0)
        return zipfile.ZipFile(buf)


class TestImportSubmissionDB(ImportSubmissionTestBase, TestCase):
    """DB-only assertions; image saves are skipped here."""

    def _import(self):
        zip_ref = self._zip_with_images({})
        try:
            return import_submission(
                self._parsed_submission(),
                tally=self.tally,
                bundle=self.bundle,
                uploaded_by=self.user,
                zip_ref=zip_ref,
            )
        finally:
            zip_ref.close()

    def test_creates_pvp_submission_with_raw_payloads(self):
        submission = self._import()
        self.assertIsInstance(submission, PvpSubmission)
        submission.refresh_from_db()
        self.assertEqual(submission.barcode, "111")
        self.assertEqual(submission.odk_instance_id, "uuid:rf-1")
        self.assertEqual(submission.round1_raw, {"131301": 10, "131302": 8})
        self.assertEqual(submission.round2_raw, {"131301": 12, "131302": 9})
        self.assertEqual(
            submission.recon_raw[
                "reconciliation_r2-number_voter_cards_r2"
            ],
            121,
        )

    def test_writes_de1_results_per_candidate_with_round2_votes(self):
        self._import()
        results = Result.objects.filter(result_form=self.result_form)
        self.assertEqual(results.count(), 2)
        for r in results:
            self.assertEqual(r.entry_version, EntryVersion.DATA_ENTRY_1)
            self.assertTrue(r.active)
            self.assertEqual(r.user_id, self.user.id)
        votes_by_cid = {r.candidate.candidate_id: r.votes for r in results}
        self.assertEqual(votes_by_cid, {131301: 12, 131302: 9})

    def test_writes_de1_recon_form_from_round2_recon(self):
        self._import()
        recons = ReconciliationForm.objects.filter(
            result_form=self.result_form,
        )
        self.assertEqual(recons.count(), 1)
        recon = recons.get()
        self.assertEqual(recon.entry_version, EntryVersion.DATA_ENTRY_1)
        self.assertTrue(recon.active)
        self.assertEqual(recon.user_id, self.user.id)
        # number_of_voters derived from station.registrants per the plan.
        self.assertEqual(recon.number_of_voters, 300)
        self.assertEqual(recon.number_of_voter_cards_in_the_ballot_box, 121)
        self.assertEqual(recon.number_valid_votes, 118)
        self.assertEqual(recon.number_invalid_votes, 3)
        self.assertEqual(recon.number_sorted_and_counted, 121)
        self.assertIsNone(recon.ballot_number_from)
        self.assertIsNone(recon.ballot_number_to)
        self.assertIsNone(recon.notes)

    def test_form_state_transitions_to_data_entry_2(self):
        self._import()
        self.result_form.refresh_from_db()
        self.assertEqual(self.result_form.form_state, FormState.DATA_ENTRY_2)
        self.assertEqual(
            self.result_form.previous_form_state, FormState.UNSUBMITTED,
        )
        self.assertFalse(self.result_form.duplicate_reviewed)
        self.assertEqual(self.result_form.user_id, self.user.id)

    def test_links_result_form_to_pvp_submission(self):
        submission = self._import()
        self.result_form.refresh_from_db()
        self.assertEqual(self.result_form.pvp_submission_id, submission.id)
        self.assertTrue(self.result_form.from_pvp)

    def test_creates_reversion_history_for_result_form(self):
        self._import()
        versions = Version.objects.get_for_object(self.result_form)
        self.assertGreaterEqual(versions.count(), 1)
        comment = versions.first().revision.comment
        self.assertIn("PVP import", comment)
        self.assertEqual(versions.first().revision.user_id, self.user.id)

    def test_atomic_rollback_leaves_no_partial_writes(self):
        # Use a candidate_id that doesn't exist for this tally so the
        # internal Candidate lookup raises and the @transaction.atomic
        # block rolls back.
        zip_ref = self._zip_with_images({})
        try:
            with self.assertRaises(Candidate.DoesNotExist):
                import_submission(
                    self._parsed_submission(candidates=(
                        CandidateResult(
                            candidate_id="999999", candidate_order=1,
                            round1=1, round2=1,
                        ),
                    )),
                    tally=self.tally, bundle=self.bundle,
                    uploaded_by=self.user, zip_ref=zip_ref,
                )
        finally:
            zip_ref.close()
        self.assertEqual(PvpSubmission.objects.count(), 0)
        self.assertEqual(
            Result.objects.filter(result_form=self.result_form).count(),
            0,
        )
        self.assertEqual(
            ReconciliationForm.objects.filter(
                result_form=self.result_form,
            ).count(),
            0,
        )
        self.result_form.refresh_from_db()
        self.assertEqual(self.result_form.form_state, FormState.UNSUBMITTED)


class TestImportSubmissionDE1AndDE2(ImportSubmissionTestBase, TestCase):
    """DE1_AND_DE2 mode: round1 -> DE1, round2 -> DE2, state -> QC."""

    def setUp(self):
        super().setUp()
        # Override the bundle to DE1_AND_DE2 mode.
        self.bundle.mode = PvpMode.DE1_AND_DE2
        self.bundle.save(update_fields=["mode"])

    def _parsed_de1_and_de2(self):
        # PVP guarantees round1 == round2 at parse time; mirror that.
        return self._parsed_submission(
            candidates=(
                CandidateResult(
                    candidate_id="131301", candidate_order=1,
                    round1=12, round2=12,
                ),
                CandidateResult(
                    candidate_id="131302", candidate_order=2,
                    round1=9, round2=9,
                ),
            ),
        )

    def _import(self):
        zip_ref = self._zip_with_images({})
        try:
            return import_submission(
                self._parsed_de1_and_de2(),
                tally=self.tally, bundle=self.bundle,
                uploaded_by=self.user, zip_ref=zip_ref,
            )
        finally:
            zip_ref.close()

    def test_writes_both_entry_versions(self):
        self._import()
        de1 = Result.objects.filter(
            result_form=self.result_form,
            entry_version=EntryVersion.DATA_ENTRY_1,
        )
        de2 = Result.objects.filter(
            result_form=self.result_form,
            entry_version=EntryVersion.DATA_ENTRY_2,
        )
        self.assertEqual(de1.count(), 2)
        self.assertEqual(de2.count(), 2)

    def test_de1_uses_round1_de2_uses_round2(self):
        self._import()
        de1_votes = dict(
            Result.objects.filter(
                result_form=self.result_form,
                entry_version=EntryVersion.DATA_ENTRY_1,
            ).values_list("candidate__candidate_id", "votes"),
        )
        de2_votes = dict(
            Result.objects.filter(
                result_form=self.result_form,
                entry_version=EntryVersion.DATA_ENTRY_2,
            ).values_list("candidate__candidate_id", "votes"),
        )
        # Per _parsed_de1_and_de2, both rounds match.
        self.assertEqual(de1_votes, {131301: 12, 131302: 9})
        self.assertEqual(de2_votes, {131301: 12, 131302: 9})

    def test_writes_both_reconciliation_forms(self):
        self._import()
        recons = ReconciliationForm.objects.filter(
            result_form=self.result_form, active=True,
        )
        self.assertEqual(recons.count(), 2)
        de1 = recons.get(entry_version=EntryVersion.DATA_ENTRY_1)
        de2 = recons.get(entry_version=EntryVersion.DATA_ENTRY_2)
        # DE1 recon reads from r1 columns, DE2 from r2 columns (per the
        # parsed submission default fixtures).
        self.assertEqual(de1.number_invalid_votes, 2)   # r1 invalid
        self.assertEqual(de2.number_invalid_votes, 3)   # r2 invalid
        self.assertEqual(de1.number_of_voter_cards_in_the_ballot_box, 120)
        self.assertEqual(de2.number_of_voter_cards_in_the_ballot_box, 121)

    def test_form_state_transitions_to_quality_control(self):
        self._import()
        self.result_form.refresh_from_db()
        self.assertEqual(
            self.result_form.form_state, FormState.QUALITY_CONTROL,
        )
        self.assertEqual(
            self.result_form.previous_form_state, FormState.UNSUBMITTED,
        )

    def test_links_result_form_to_pvp_submission(self):
        submission = self._import()
        self.result_form.refresh_from_db()
        self.assertEqual(self.result_form.pvp_submission_id, submission.id)
        self.assertTrue(self.result_form.from_pvp)


class TestImportSubmissionImages(ImportSubmissionTestBase, TestCase):
    """Image-saving assertions: deferred to transaction.on_commit."""

    def test_images_saved_after_commit_callback_runs(self):
        zip_ref = self._zip_with_images({
            "sig.jpg": b"sig-bytes",
            "p1.jpg": b"p1-bytes",
        })
        try:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                submission = import_submission(
                    self._parsed_submission(),
                    tally=self.tally, bundle=self.bundle,
                    uploaded_by=self.user, zip_ref=zip_ref,
                )
            self.assertGreaterEqual(len(callbacks), 1)
        finally:
            zip_ref.close()
        submission.refresh_from_db()
        self.assertTrue(submission.clerk_signature.name.endswith("sig.jpg"))
        self.assertTrue(
            submission.forms_picture_1st_page.name.endswith("p1.jpg"),
        )
        # Page 2 was None in the parsed payload — stays unset.
        self.assertFalse(submission.forms_picture_2nd_page)

    def test_image_missing_from_zip_leaves_field_null(self):
        # Only sig.jpg is in the zip; p1.jpg referenced in parsed but absent.
        zip_ref = self._zip_with_images({"sig.jpg": b"sig-bytes"})
        try:
            with self.captureOnCommitCallbacks(execute=True):
                submission = import_submission(
                    self._parsed_submission(),
                    tally=self.tally, bundle=self.bundle,
                    uploaded_by=self.user, zip_ref=zip_ref,
                )
        finally:
            zip_ref.close()
        submission.refresh_from_db()
        self.assertTrue(submission.clerk_signature.name.endswith("sig.jpg"))
        self.assertFalse(submission.forms_picture_1st_page)

    def test_no_image_files_on_disk_when_transaction_rolls_back(self):
        zip_ref = self._zip_with_images({
            "sig.jpg": b"sig-bytes",
            "p1.jpg": b"p1-bytes",
        })
        try:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with self.assertRaises(Candidate.DoesNotExist):
                    import_submission(
                        self._parsed_submission(candidates=(
                            CandidateResult(
                                candidate_id="999999", candidate_order=1,
                                round1=1, round2=1,
                            ),
                        )),
                        tally=self.tally, bundle=self.bundle,
                        uploaded_by=self.user, zip_ref=zip_ref,
                    )
        finally:
            zip_ref.close()
        # The on_commit callback was never queued because the inner atomic
        # block rolled back; even if it had been, captureOnCommitCallbacks
        # only fires callbacks for committed transactions.
        self.assertEqual(callbacks, [])
        # Media root is otherwise empty — no orphan image files.
        # (override_settings + tearDown clean the dir between tests.)
        leftovers = []
        for root, _, files in os.walk(self._media_root):
            for f in files:
                leftovers.append(os.path.join(root, f))
        self.assertEqual(leftovers, [])


class TestImportBundle(ImportSubmissionTestBase, TestCase):
    """Bundle-level orchestrator: walks validated submissions, flips status."""

    def setUp(self):
        super().setUp()
        # Three result_forms with distinct barcodes; each maps to its own
        # candidate set (reuse the two candidates created in the parent
        # setUp; PvpSubmission writes Result rows referencing them).
        self.rf2 = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=self.station.station_number,
            barcode="222", form_state=FormState.UNSUBMITTED,
            serial_number=2,
        )
        self.rf3 = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=self.station.station_number,
            barcode="333", form_state=FormState.UNSUBMITTED,
            serial_number=3,
        )

    def _three_submissions(self):
        return [
            self._parsed_submission(
                odk_instance_id="uuid:rf-1", barcode="111",
            ),
            self._parsed_submission(
                odk_instance_id="uuid:rf-2", barcode="222",
            ),
            self._parsed_submission(
                odk_instance_id="uuid:rf-3", barcode="333",
            ),
        ]

    def test_imports_all_rows_and_marks_completed(self):
        zip_ref = self._zip_with_images({})
        try:
            returned = import_bundle(
                bundle=self.bundle,
                submissions=self._three_submissions(),
                tally=self.tally,
                uploaded_by=self.user,
                zip_ref=zip_ref,
            )
        finally:
            zip_ref.close()
        self.assertIs(returned, self.bundle)
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, PvpBundleStatus.COMPLETED)
        self.assertEqual(self.bundle.number_of_submissions, 3)
        self.assertIsNotNone(self.bundle.imported_at)
        self.assertEqual(self.bundle.submissions.count(), 3)
        for rf in (self.result_form, self.rf2, self.rf3):
            rf.refresh_from_db()
            self.assertTrue(rf.from_pvp)
            self.assertEqual(rf.form_state, FormState.DATA_ENTRY_2)

    def test_empty_submission_list_marks_completed_with_zero(self):
        zip_ref = self._zip_with_images({})
        try:
            import_bundle(
                bundle=self.bundle, submissions=[],
                tally=self.tally, uploaded_by=self.user, zip_ref=zip_ref,
            )
        finally:
            zip_ref.close()
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, PvpBundleStatus.COMPLETED)
        self.assertEqual(self.bundle.number_of_submissions, 0)
        self.assertIsNotNone(self.bundle.imported_at)

    def test_failure_marks_bundle_failed_reraises_and_rolls_back_all(self):
        # Second submission references a candidate_id that doesn't exist.
        # Under all-or-nothing semantics the first submission must also
        # be rolled back so the bundle leaves no partial trace.
        bad = self._parsed_submission(
            odk_instance_id="uuid:rf-2", barcode="222",
            candidates=(
                CandidateResult(
                    candidate_id="999999", candidate_order=1,
                    round1=1, round2=1,
                ),
            ),
        )
        good = self._parsed_submission(
            odk_instance_id="uuid:rf-1", barcode="111",
        )
        zip_ref = self._zip_with_images({})
        try:
            with self.assertRaises(Candidate.DoesNotExist):
                import_bundle(
                    bundle=self.bundle, submissions=[good, bad],
                    tally=self.tally, uploaded_by=self.user,
                    zip_ref=zip_ref,
                )
        finally:
            zip_ref.close()
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, PvpBundleStatus.FAILED)
        self.assertIsNone(self.bundle.imported_at)
        # All-or-nothing: nothing persisted.
        self.assertEqual(self.bundle.submissions.count(), 0)
        self.result_form.refresh_from_db()
        self.assertEqual(self.result_form.form_state, FormState.UNSUBMITTED)
        self.assertFalse(self.result_form.from_pvp)
