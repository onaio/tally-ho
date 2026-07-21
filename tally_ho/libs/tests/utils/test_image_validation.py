import io

from django.core.exceptions import ValidationError
from django.test import TestCase
from PIL import Image

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
