"""Tests for the PVP super-admin view triplet (upload / confirm / result).

The celery enqueue in PvpConfirmView.post is patched out — it's covered
end-to-end in test_async_pvp_import.py.
"""

import csv
import io
import shutil
import tempfile
import zipfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.views.pvp import (
    PvpConfirmView, PvpResultView, PvpUploadView,
)
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase, configure_messages, create_ballot, create_center,
    create_electrol_race, create_result_form, create_station, create_tally,
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


def _zip_bytes(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        csv_buf = io.StringIO()
        w = csv.DictWriter(csv_buf, fieldnames=CSV_HEADERS,
                           extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        zf.writestr("candidate_results.csv", csv_buf.getvalue())
        zf.writestr("media/sig.jpg", b"sig")
        zf.writestr("media/p1.jpg", b"p1")
    return buf.getvalue()


class _PvpViewTestBase(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user(username="admin", password="pass")
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.tally.pvp_mode = PvpMode.DE1_ONLY
        self.tally.save()

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
            full_name="Cand", active=True,
        )
        self.result_form = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=self.station.station_number,
            barcode="111", form_state=FormState.UNSUBMITTED,
        )

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)


class TestPvpUploadView(_PvpViewTestBase, TestCase):
    def test_get_renders_form(self):
        view = PvpUploadView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.id)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_zip_creates_bundle_and_redirects_to_confirm(self):
        view = PvpUploadView.as_view()
        zip_bytes = _zip_bytes([
            _csv_row(instance_id="uuid:1", barcode="111",
                     candidate_id=131301, order=1, r2=12),
        ])
        upload = SimpleUploadedFile(
            "bundle.zip", zip_bytes, content_type="application/zip",
        )
        request = self.factory.post("/", data={"zip_file": upload})
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.id)
        self.assertEqual(response.status_code, 302)
        bundle = PvpUploadBundle.objects.get()
        self.assertEqual(bundle.status, PvpBundleStatus.PENDING)
        self.assertEqual(bundle.uploaded_by_id, self.user.id)
        self.assertTrue(bundle.zip_file.name.endswith("bundle.zip"))
        self.assertIn(
            f"/pvp/confirm/{bundle.id}/", response["Location"],
        )

    def test_post_invalid_zip_shows_error_no_bundle_created(self):
        view = PvpUploadView.as_view()
        # Zip is structurally valid but missing candidate_results.csv.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w") as zf:
            zf.writestr("README.txt", b"oops")
        upload = SimpleUploadedFile(
            "bundle.zip", buf.getvalue(),
            content_type="application/zip",
        )
        request = self.factory.post("/", data={"zip_file": upload})
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PvpUploadBundle.objects.count(), 0)


class TestPvpConfirmView(_PvpViewTestBase, TestCase):
    def _make_pending_bundle(self):
        zip_bytes = _zip_bytes([
            _csv_row(instance_id="uuid:1", barcode="111",
                     candidate_id=131301, order=1, r2=12),
            _csv_row(instance_id="uuid:2", barcode="999",  # bad barcode
                     candidate_id=131301, order=1, r2=5),
        ])
        bundle = PvpUploadBundle.objects.create(
            tally=self.tally, uploaded_by=self.user,
            filename="bundle.zip",
        )
        bundle.zip_file = SimpleUploadedFile(
            "bundle.zip", zip_bytes, content_type="application/zip",
        )
        bundle.save()
        return bundle

    def test_get_renders_will_import_and_will_skip(self):
        bundle = self._make_pending_bundle()
        view = PvpConfirmView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(
            request, tally_id=self.tally.id, bundle_id=bundle.id,
        )
        self.assertEqual(response.status_code, 200)
        # 1 valid (barcode=111) + 1 invalid (barcode=999, not in tally).
        response.render()
        body = response.content.decode()
        self.assertIn("Will import (1)", body)
        self.assertIn("Will skip (1)", body)
        self.assertIn("barcode_not_found", body)

    @mock.patch(
        "tally_ho.apps.tally.views.pvp.async_pvp_import",
    )
    def test_post_enqueues_celery_and_redirects_to_result(self, mock_task):
        bundle = self._make_pending_bundle()
        view = PvpConfirmView.as_view()
        request = self.factory.post("/")
        configure_messages(request)
        request.user = self.user
        request.session = {}
        response = view(
            request, tally_id=self.tally.id, bundle_id=bundle.id,
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_called_once_with(
            bundle_id=bundle.id, user_id=self.user.id,
        )
        self.assertIn(
            f"/pvp/result/{bundle.id}/", response["Location"],
        )


class TestPvpResultView(_PvpViewTestBase, TestCase):
    def test_get_renders_status(self):
        bundle = PvpUploadBundle.objects.create(
            tally=self.tally, uploaded_by=self.user, filename="b.zip",
            status=PvpBundleStatus.COMPLETED, number_of_submissions=3,
        )
        view = PvpResultView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(
            request, tally_id=self.tally.id, bundle_id=bundle.id,
        )
        self.assertEqual(response.status_code, 200)
        response.render()
        body = response.content.decode()
        self.assertIn("COMPLETED", body)
        self.assertIn("Submissions imported", body)
        self.assertIn(">3<", body)


class TestPvpViewPermissions(_PvpViewTestBase, TestCase):
    def test_non_super_admin_forbidden(self):
        # Re-create user without super-admin group.
        from django.core.exceptions import PermissionDenied
        self._create_and_login_user(username="rando", password="pass")
        # No group added.
        view = PvpUploadView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        with self.assertRaises(PermissionDenied):
            view(request, tally_id=self.tally.id)
