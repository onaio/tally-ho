"""Verify that raw bytes are a real, allowed image before storing them.

Loading arbitrary uploaded or imported files is the obvious attack
surface, even for an airgapped deployment. Every ingest boundary (the
PVP bundle import and, in a later release, manual upload) runs the bytes
through Pillow here before anything is persisted, so a file that is not a
genuine JPEG or PNG never reaches disk or a browser.
"""

import io
import warnings

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

# Cap decoded pixel count to guard against decompression-bomb DoS — a
# small file can declare enormous dimensions.
Image.MAX_IMAGE_PIXELS = 64_000_000  # ~64 megapixels

# Allowed Pillow formats and the content type served for each.
IMAGE_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def validate_image_bytes(data):
    """Return the Pillow format (e.g. ``"JPEG"``) if ``data`` is a valid
    JPEG or PNG, else raise ``ValidationError``.

    Uses Pillow to confirm the bytes decode as a real image rather than
    trusting a filename or extension, and rejects decompression bombs.
    """
    try:
        with warnings.catch_warnings():
            # Treat an oversized-image warning as a hard failure.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as img:
                image_format = img.format
                img.verify()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ) as exc:
        raise ValidationError(_("File is not a valid image.")) from exc

    if image_format not in IMAGE_CONTENT_TYPES:
        raise ValidationError(
            _("Unsupported image format: %(image_format)s") % {
                "image_format": image_format,
            }
        )
    return image_format
