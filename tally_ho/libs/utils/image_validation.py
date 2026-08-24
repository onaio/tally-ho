"""Verify that raw bytes are a real, allowed image before storing them.

Every ingest boundary runs bytes through here before anything is
persisted, so a file that is not a genuine JPEG, PNG, or WebP never
reaches disk or a browser.
"""

import io

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_PIXELS = 50_000_000  # 50 megapixels

IMAGE_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def validate_image_bytes(data):
    """Return the Pillow format if ``data`` is a valid JPEG, PNG, or
    WebP, else raise ``ValidationError``.

    Dimensions are checked against the header without decoding pixels,
    so nothing mutates Pillow's process-global cap and the guard stays
    thread-safe.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            image_format = img.format
            width, height = img.size
            img.verify()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ) as exc:
        raise ValidationError(_("File is not a valid image.")) from exc

    if width * height > MAX_IMAGE_PIXELS:
        raise ValidationError(_("File is not a valid image."))

    if image_format not in IMAGE_CONTENT_TYPES:
        raise ValidationError(
            _("Unsupported image format: %(image_format)s") % {
                "image_format": image_format,
            }
        )
    return image_format
