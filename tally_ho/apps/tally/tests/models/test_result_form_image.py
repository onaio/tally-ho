import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.models.result_form_image import (
    ResultFormImage,
    build_result_form_image_path,
)
from tally_ho.libs.models.enums.result_form_image_kind import (
    ResultFormImageKind,
)
from tally_ho.libs.models.enums.result_form_image_source import (
    ResultFormImageSource,
)
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_result_form,
    create_tally,
)


class TestBuildResultFormImagePath(SimpleTestCase):
    """The path helper on its own — no model, no storage."""

    def test_builds_path_from_ids_and_basename(self):
        self.assertEqual(
            build_result_form_image_path(7, 42, "photo.jpg"),
            "form_images/7/42/photo.jpg",
        )

    def test_strips_any_directory_prefix(self):
        self.assertEqual(
            build_result_form_image_path(7, 42, "a/b/c.jpg"),
            "form_images/7/42/c.jpg",
        )

    def test_strips_windows_style_directory_prefix(self):
        # Zip entries may legally carry backslash separators, and storage
        # names are POSIX regardless of the host — the leaf must be taken
        # from either separator so a prefix can never survive into the path.
        self.assertEqual(
            build_result_form_image_path(7, 42, r"..\..\evil.jpg"),
            "form_images/7/42/evil.jpg",
        )

    def test_stringifies_non_string_ids(self):
        self.assertEqual(
            build_result_form_image_path("7", 42, "photo.jpg"),
            "form_images/7/42/photo.jpg",
        )

    def test_uses_posix_separators(self):
        path = build_result_form_image_path(7, 42, "photo.jpg")
        self.assertNotIn("\\", path)


class TestResultFormImage(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self.result_form = create_result_form(tally=self.tally)
        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def _create_image(self, **overrides):
        defaults = {
            "tally": self.tally,
            "result_form": self.result_form,
            "image": SimpleUploadedFile(
                "photo.jpg", b"jpg-bytes", content_type="image/jpeg",
            ),
        }
        defaults.update(overrides)
        return ResultFormImage.objects.create(**defaults)

    def test_defaults(self):
        image = self._create_image()
        image.refresh_from_db()
        self.assertEqual(image.source, ResultFormImageSource.UPLOAD)
        self.assertEqual(image.kind, ResultFormImageKind.SUPPORTING)
        self.assertIsNone(image.caption)
        self.assertIsNone(image.uploaded_by_id)
        self.assertIsNone(image.pvp_submission_id)
        # Live by default (soft-delete flag); format blank until verified.
        self.assertTrue(image.active)
        self.assertEqual(image.image_format, "")

    def test_reverse_accessor(self):
        self._create_image()
        self._create_image()
        self.assertEqual(self.result_form.images.count(), 2)

    def test_image_path_uses_tally_and_result_form_id(self):
        image = self._create_image()
        image.refresh_from_db()
        expected_prefix = f"form_images/{self.tally.id}/{self.result_form.id}/"
        self.assertTrue(
            image.image.name.startswith(expected_prefix),
            msg=f"image path was {image.image.name}",
        )

    def test_resaving_leaves_image_path_untouched(self):
        # Only an uncommitted file is repathed. Re-saving a stored image
        # must not prefix the path a second time.
        image = self._create_image()
        stored_name = image.image.name
        image.caption = "edited"
        image.save()
        image.refresh_from_db()
        self.assertEqual(image.image.name, stored_name)

    def test_pvp_import_row_links_submission(self):
        bundle = PvpUploadBundle.objects.create(
            tally=self.tally,
            uploaded_by=self.user,
            filename="bundle.zip",
        )
        submission = PvpSubmission.objects.create(
            tally=self.tally,
            bundle=bundle,
            odk_instance_id="uuid:1",
            odk_form_id="results_1",
            barcode=self.result_form.barcode,
        )
        image = self._create_image(
            source=ResultFormImageSource.PVP_IMPORT,
            kind=ResultFormImageKind.CLERK_SIGNATURE,
            pvp_submission=submission,
        )
        image.refresh_from_db()
        self.assertEqual(image.source, ResultFormImageSource.PVP_IMPORT)
        self.assertEqual(image.kind, ResultFormImageKind.CLERK_SIGNATURE)
        self.assertEqual(image.pvp_submission_id, submission.id)
        # Reverse accessor from the submission.
        self.assertEqual(submission.applied_images.count(), 1)

    def test_uploaded_by_round_trip(self):
        image = self._create_image(uploaded_by=self.user)
        image.refresh_from_db()
        self.assertEqual(image.uploaded_by_id, self.user.id)

    def test_str(self):
        image = self._create_image()
        rendered = str(image)
        self.assertIn("ResultFormImage", rendered)
        self.assertIn(str(image.result_form_id), rendered)
