import io
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from PIL import Image

from tally_ho.libs.utils import image_validation
from tally_ho.libs.utils.image_validation import validate_image_bytes


def _image_bytes(image_format="PNG", size=(2, 2)):
    buf = io.BytesIO()
    Image.new("RGB", size).save(buf, format=image_format)
    return buf.getvalue()


class TestValidateImageBytes(TestCase):
    def test_accepts_png(self):
        self.assertEqual(validate_image_bytes(_image_bytes("PNG")), "PNG")

    def test_accepts_jpeg(self):
        self.assertEqual(validate_image_bytes(_image_bytes("JPEG")), "JPEG")

    def test_accepts_webp(self):
        self.assertEqual(validate_image_bytes(_image_bytes("WEBP")), "WEBP")

    def test_rejects_non_image_bytes(self):
        with self.assertRaises(ValidationError):
            validate_image_bytes(b"not an image at all")

    def test_rejects_html_masquerading_as_image(self):
        with self.assertRaises(ValidationError):
            validate_image_bytes(b"<html><script>alert(1)</script></html>")

    def test_rejects_disallowed_format(self):
        with self.assertRaises(ValidationError):
            validate_image_bytes(_image_bytes("GIF"))

    def test_rejects_truncated_image(self):
        data = _image_bytes("JPEG", size=(64, 64))
        with self.assertRaises(ValidationError):
            validate_image_bytes(data[: len(data) // 2])

    def test_rejects_decompression_bomb(self):
        # A legitimately-decodable image whose pixel count exceeds the cap
        # must be rejected. Patch the module cap low so a small test image
        # trips it.
        data = _image_bytes("PNG", size=(100, 100))  # 10_000 px
        with mock.patch.object(image_validation, "MAX_IMAGE_PIXELS", 16):
            with self.assertRaises(ValidationError):
                validate_image_bytes(data)

    def test_does_not_mutate_pillow_global_cap(self):
        # The dimension guard is enforced locally, so validation must never
        # touch Pillow's process-global cap — mutating it is not thread-safe
        # under a threaded worker. Assert it is untouched on both the
        # accept path and the reject (oversized) path.
        before = Image.MAX_IMAGE_PIXELS
        validate_image_bytes(_image_bytes("PNG"))
        self.assertEqual(Image.MAX_IMAGE_PIXELS, before)

        data = _image_bytes("PNG", size=(100, 100))
        with mock.patch.object(image_validation, "MAX_IMAGE_PIXELS", 16):
            with self.assertRaises(ValidationError):
                validate_image_bytes(data)
        self.assertEqual(Image.MAX_IMAGE_PIXELS, before)
