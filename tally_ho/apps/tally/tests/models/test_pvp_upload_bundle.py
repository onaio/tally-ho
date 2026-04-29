import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus
from tally_ho.libs.tests.test_base import TestBase, create_tally


class TestPvpUploadBundle(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def _create_bundle(self, **overrides):
        defaults = {
            "tally": self.tally,
            "uploaded_by": self.user,
            "filename": "results-bundle.zip",
        }
        defaults.update(overrides)
        return PvpUploadBundle.objects.create(**defaults)

    def test_defaults(self):
        bundle = self._create_bundle()
        bundle.refresh_from_db()
        self.assertEqual(bundle.status, PvpBundleStatus.PENDING)
        self.assertEqual(bundle.number_of_submissions, 0)
        self.assertIsNone(bundle.imported_at)
        self.assertIsNotNone(bundle.created_date)

    def test_required_fields_round_trip(self):
        bundle = self._create_bundle(filename="2026-04-29-bundle.zip")
        bundle.refresh_from_db()
        self.assertEqual(bundle.tally_id, self.tally.id)
        self.assertEqual(bundle.uploaded_by_id, self.user.id)
        self.assertEqual(bundle.filename, "2026-04-29-bundle.zip")

    def test_status_transitions(self):
        bundle = self._create_bundle()
        for status in (
            PvpBundleStatus.IMPORTING,
            PvpBundleStatus.COMPLETED,
            PvpBundleStatus.FAILED,
        ):
            bundle.status = status
            bundle.save()
            bundle.refresh_from_db()
            self.assertEqual(bundle.status, status)

    def test_zip_file_path_uses_tally_and_bundle_id(self):
        bundle = self._create_bundle()
        upload = SimpleUploadedFile(
            "results.zip", b"zip-content", content_type="application/zip",
        )
        bundle.zip_file = upload
        bundle.save()
        bundle.refresh_from_db()
        expected_prefix = (
            f"pvp/bundles/{self.tally.id}/{bundle.id}/"
        )
        self.assertTrue(
            bundle.zip_file.name.startswith(expected_prefix),
            msg=f"zip path was {bundle.zip_file.name}",
        )
        self.assertTrue(bundle.zip_file.name.endswith("results.zip"))
