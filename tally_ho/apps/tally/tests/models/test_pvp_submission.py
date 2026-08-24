import shutil
import tempfile

from django.db import IntegrityError
from django.test import override_settings

from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.libs.tests.test_base import TestBase, create_tally


class TestPvpSubmission(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self.bundle = PvpUploadBundle.objects.create(
            tally=self.tally,
            uploaded_by=self.user,
            filename="bundle.zip",
        )
        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def _create_submission(self, **overrides):
        defaults = {
            "tally": self.tally,
            "bundle": self.bundle,
            "odk_instance_id": "uuid:abc-123",
            "odk_form_id": "results_14065",
            "barcode": "12345",
        }
        defaults.update(overrides)
        return PvpSubmission.objects.create(**defaults)

    def test_required_fields_round_trip(self):
        sub = self._create_submission(
            staff_user_name="clerk1",
        )
        sub.refresh_from_db()
        self.assertEqual(sub.tally_id, self.tally.id)
        self.assertEqual(sub.bundle_id, self.bundle.id)
        self.assertEqual(sub.odk_instance_id, "uuid:abc-123")
        self.assertEqual(sub.odk_form_id, "results_14065")
        self.assertEqual(sub.barcode, "12345")
        self.assertEqual(sub.staff_user_name, "clerk1")

    def test_json_payloads_default_to_empty_dict(self):
        sub = self._create_submission()
        sub.refresh_from_db()
        self.assertEqual(sub.round1_raw, {})
        self.assertEqual(sub.round2_raw, {})
        self.assertEqual(sub.recon_raw, {})

    def test_json_payloads_round_trip(self):
        sub = self._create_submission(
            round1_raw={"cand_1": 10, "cand_2": 20},
            round2_raw={"cand_1": 12, "cand_2": 22},
            recon_raw={
                "reconciliation_r2-number_ballots_received_r2": 100,
            },
        )
        sub.refresh_from_db()
        self.assertEqual(sub.round1_raw["cand_2"], 20)
        self.assertEqual(sub.round2_raw["cand_2"], 22)
        self.assertEqual(
            sub.recon_raw["reconciliation_r2-number_ballots_received_r2"],
            100,
        )

    def test_unique_per_tally_and_instance_id(self):
        self._create_submission(odk_instance_id="uuid:dup")
        with self.assertRaises(IntegrityError):
            self._create_submission(odk_instance_id="uuid:dup")

    def test_same_instance_id_allowed_across_tallies(self):
        self._create_submission(odk_instance_id="uuid:shared")
        other_tally = create_tally(name="otherTally")
        other_bundle = PvpUploadBundle.objects.create(
            tally=other_tally,
            uploaded_by=self.user,
            filename="other.zip",
        )
        other = PvpSubmission.objects.create(
            tally=other_tally,
            bundle=other_bundle,
            odk_instance_id="uuid:shared",
            odk_form_id="results_99",
            barcode="999",
        )
        self.assertNotEqual(other.id, None)

    def test_bundle_reverse_accessor(self):
        # related_name='submissions' makes bundle.submissions usable.
        self._create_submission(odk_instance_id="uuid:1")
        self._create_submission(odk_instance_id="uuid:2")
        self.assertEqual(self.bundle.submissions.count(), 2)
