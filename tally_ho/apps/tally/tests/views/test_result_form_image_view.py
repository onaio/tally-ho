import os
import shutil
import tempfile

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings

from tally_ho.apps.tally.models.result_form_image import ResultFormImage
from tally_ho.apps.tally.views.result_form_image import ResultFormImageView
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase, create_result_form, create_tally,
)


class TestResultFormImageView(TestBase, TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user(username="clerk", password="pass")
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

        self.tally = create_tally()
        self.result_form = create_result_form(
            tally=self.tally, barcode="img-1",
        )
        self.image = ResultFormImage.objects.create(
            tally=self.tally,
            result_form=self.result_form,
            image=SimpleUploadedFile(
                "p.jpg", b"the-bytes", content_type="image/jpeg",
            ),
            image_format="JPEG",
        )

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def _get(self, user, image_id=None):
        request = self.factory.get("/")
        request.user = user
        request.session = {}
        return ResultFormImageView.as_view()(
            request,
            tally_id=self.tally.id,
            image_id=image_id or self.image.id,
        )

    def test_authed_with_access_returns_bytes(self):
        response = self._get(self.user)
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content)
        self.assertEqual(content, b"the-bytes")

    def test_response_declares_image_type_and_nosniff(self):
        response = self._get(self.user)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_no_access_forbidden(self):
        other = self._create_user(username="rando", password="pass")
        with self.assertRaises(PermissionDenied):
            self._get(other)

    def test_anonymous_redirects_to_login(self):
        response = self._get(AnonymousUser())
        self.assertEqual(response.status_code, 302)

    def test_missing_file_raises_404(self):
        # Row exists but the underlying file is gone from storage.
        os.remove(self.image.image.path)
        with self.assertRaises(Http404):
            self._get(self.user)

    def test_content_type_follows_stored_format(self):
        cases = {
            "PNG": "image/png",
            "WEBP": "image/webp",
            "": "application/octet-stream",  # unknown/blank fallback
        }
        for image_format, expected in cases.items():
            image = ResultFormImage.objects.create(
                tally=self.tally,
                result_form=self.result_form,
                image=SimpleUploadedFile(
                    "x.bin", b"bytes", content_type="application/octet-stream",
                ),
                image_format=image_format,
            )
            response = self._get(self.user, image_id=image.id)
            self.assertEqual(
                response["Content-Type"], expected,
                msg=f"format {image_format!r}",
            )
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_cross_tally_image_not_reachable_via_this_tally_scope(self):
        # self.user is a TALLY_MANAGER (access to every tally). The URL
        # scope (tally_id) must still gate which image is served: an image
        # belonging to tally B cannot be fetched by pinning tally A's id.
        other_tally = create_tally(name="tallyB")
        other_form = create_result_form(tally=other_tally, barcode="b-1")
        other_image = ResultFormImage.objects.create(
            tally=other_tally,
            result_form=other_form,
            image=SimpleUploadedFile(
                "b.jpg", b"b-bytes", content_type="image/jpeg",
            ),
            image_format="JPEG",
        )
        # tally_id from the URL is self.tally (A); image belongs to B.
        with self.assertRaises(Http404):
            self._get(self.user, image_id=other_image.id)
