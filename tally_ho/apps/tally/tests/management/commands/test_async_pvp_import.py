"""End-to-end async test for the PVP import celery task.

Requires a running Celery broker (redis) — same as other ``test_async_*``
tests in this directory. Locally, that means redis on :6379; in CI the
job's ``services:`` block provides it.
"""

import csv
import io
import shutil
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings

from tally_ho.apps.tally.management.commands.async_pvp_import import (
    async_pvp_import,
)
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.tests.test_base import (
    create_ballot, create_center, create_electrol_race,
    create_result_form, create_station, create_tally,
)


CSV_HEADERS = [
    "pos", "candidate_id", "candidate_order", "candidate_name",
    "candidate_result_round1", "candidate_result_round2",
    "meta-instanceID", "KEY", "xml_form_id", "center_id",
    "station_number", "staff_user_name", "ballot_number", "race_type",
    "barcode",
    "reconciliation_r1-number_ballots_received_r1",
    "reconciliation_r1-number_voter_cards_r1",
    "reconciliation_r1-number_valid_ballots_r1",
    "reconciliation_r1-number_invalid_ballots_r1",
    "reconciliation_r1-number_ballots_inside_box_r1",
    "reconciliation_r2-number_ballots_received_r2",
    "reconciliation_r2-number_voter_cards_r2",
    "reconciliation_r2-number_valid_ballots_r2",
    "reconciliation_r2-number_invalid_ballots_r2",
    "reconciliation_r2-number_ballots_inside_box_r2",
    "clerk_signature", "forms_picture_1st_page", "forms_picture_2nd_page",
]


def _csv_row(*, instance_id, barcode, candidate_id, order, r2):
    return {
        "pos": str(order), "candidate_id": str(candidate_id),
        "candidate_order": str(order),
        "candidate_name": f"Candidate {candidate_id}",
        "candidate_result_round1": str(r2),
        "candidate_result_round2": str(r2),
        "meta-instanceID": instance_id,
        "KEY": f"{instance_id}/candidate_results[{order}]",
        "xml_form_id": "results_14065", "center_id": "14065",
        "station_number": "3", "staff_user_name": "clerk",
        "ballot_number": "1313", "race_type": "Individual",
        "barcode": barcode,
        "reconciliation_r1-number_ballots_received_r1": "300",
        "reconciliation_r1-number_voter_cards_r1": "120",
        "reconciliation_r1-number_valid_ballots_r1": "118",
        "reconciliation_r1-number_invalid_ballots_r1": "2",
        "reconciliation_r1-number_ballots_inside_box_r1": "120",
        "reconciliation_r2-number_ballots_received_r2": "300",
        "reconciliation_r2-number_voter_cards_r2": "121",
        "reconciliation_r2-number_valid_ballots_r2": "118",
        "reconciliation_r2-number_invalid_ballots_r2": "3",
        "reconciliation_r2-number_ballots_inside_box_r2": "121",
        "clerk_signature": "sig.jpg",
        "forms_picture_1st_page": "p1.jpg",
        "forms_picture_2nd_page": "",
    }


def _build_zip_bytes(rows, image_filenames):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=CSV_HEADERS,
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        zf.writestr("candidate_results.csv", csv_buf.getvalue())
        for name in image_filenames:
            zf.writestr(f"media/{name}", b"image-bytes")
    return buf.getvalue()


class AsyncPvpImportTestCase(TransactionTestCase):
    # The test invokes the celery task via .apply() so it runs
    # synchronously in-process. No broker / no worker needed.

    def setUp(self):
        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

        self.tally = create_tally()
        self.tally.pvp_mode = PvpMode.DE1_ONLY
        self.tally.save(update_fields=["pvp_mode"])

        self.electrol_race = create_electrol_race(
            self.tally,
            election_level="presidential", ballot_name="Presidential",
        )
        self.ballot = create_ballot(
            self.tally, electrol_race=self.electrol_race, number=1,
        )
        self.center = create_center(tally=self.tally)
        self.station = create_station(
            center=self.center, tally=self.tally,
            station_number=3, registrants=300,
        )
        Candidate.objects.create(
            ballot=self.ballot, electrol_race=self.electrol_race,
            tally=self.tally, candidate_id=131301, order=1,
            full_name="Cand One", active=True,
        )
        Candidate.objects.create(
            ballot=self.ballot, electrol_race=self.electrol_race,
            tally=self.tally, candidate_id=131302, order=2,
            full_name="Cand Two", active=True,
        )
        self.result_form = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=self.station.station_number,
            barcode="111", form_state=FormState.UNSUBMITTED,
        )
        # Need a UserProfile with an id we can pass to the celery task.
        self.user = UserProfile.objects.create(
            username="pvp_admin", password="pass",
        )

        # Build the bundle row with a real zip on disk.
        zip_bytes = _build_zip_bytes(
            rows=[
                _csv_row(instance_id="uuid:1", barcode="111",
                         candidate_id=131301, order=1, r2=12),
                _csv_row(instance_id="uuid:1", barcode="111",
                         candidate_id=131302, order=2, r2=9),
            ],
            image_filenames={"sig.jpg", "p1.jpg"},
        )
        self.bundle = PvpUploadBundle.objects.create(
            tally=self.tally, uploaded_by=self.user,
            filename="bundle.zip",
        )
        self.bundle.zip_file = SimpleUploadedFile(
            "bundle.zip", zip_bytes, content_type="application/zip",
        )
        self.bundle.save()

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def test_async_pvp_import_end_to_end(self):
        # apply() runs the task synchronously in-process regardless of
        # broker state, which keeps the test deterministic.
        async_pvp_import.apply(
            kwargs={"bundle_id": self.bundle.id, "user_id": self.user.id},
        )

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, PvpBundleStatus.COMPLETED)
        self.assertEqual(self.bundle.number_of_submissions, 1)
        self.assertIsNotNone(self.bundle.imported_at)

        self.assertEqual(PvpSubmission.objects.count(), 1)
        self.result_form.refresh_from_db()
        self.assertTrue(self.result_form.from_pvp)
        self.assertEqual(
            self.result_form.form_state, FormState.DATA_ENTRY_2,
        )

    def test_async_pvp_import_marks_failed_when_parse_raises(self):
        # Corrupt the persisted zip so parse_bundle raises. Without the
        # try/except in async_pvp_import this would leave the bundle
        # stuck in IMPORTING.
        with open(self.bundle.zip_file.path, "wb") as fh:
            fh.write(b"not a zip")

        with self.assertRaises(Exception):
            async_pvp_import.apply(
                kwargs={
                    "bundle_id": self.bundle.id, "user_id": self.user.id,
                },
                throw=True,
            )

        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.status, PvpBundleStatus.FAILED)
        self.assertIsNone(self.bundle.imported_at)
        self.assertEqual(PvpSubmission.objects.count(), 0)
