"""Verify that raw bytes are a real, allowed image before storing them.

Loading arbitrary uploaded or imported files is the obvious attack
surface, even for an airgapped deployment. Every ingest boundary (the
PVP bundle parser and, in a later release, manual upload) runs the bytes
through Pillow here before anything is persisted, so a file that is not a
genuine JPEG, PNG, or WebP never reaches disk or a browser.
"""

import io

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

# Cap declared image dimensions to guard against decompression-bomb DoS —
# a tiny file can declare enormous dimensions. Set generously above any
# single Android capture (the bundle's only image source; ~200 MB
# worst-case decode). Enforced against the header-declared dimensions we
# read from Pillow, so this holds without touching Pillow's
# process-global ``Image.MAX_IMAGE_PIXELS`` (which is not thread-safe to
# mutate under a threaded worker).
MAX_IMAGE_PIXELS = 50_000_000  # 50 megapixels

# Allowed Pillow formats and the content type served for each.
IMAGE_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def validate_image_bytes(data):
    """Return the Pillow format (e.g. ``"JPEG"``) if ``data`` is a valid
    JPEG, PNG, or WebP, else raise ``ValidationError``.

    Uses Pillow to confirm the bytes decode as a real image rather than
    trusting a filename or extension, and rejects decompression bombs.

    ``Image.open()`` reads the header (format + declared dimensions)
    without decoding pixels; those dimensions are checked against
    ``MAX_IMAGE_PIXELS`` here. Pillow's own ``DecompressionBombError``
    (raised at ``open()`` for extreme dimensions, on its process-global
    default) is also caught as a backstop. This keeps the guard
    thread-safe — nothing mutates Pillow's global cap.
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
