from django.db import models
from enumfields import EnumIntegerField

from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.result_form_image_kind import (
    ResultFormImageKind,
)
from tally_ho.libs.models.enums.result_form_image_source import (
    ResultFormImageSource,
)


def result_form_image_upload_to(instance, filename):
    """Path: form_images/<tally_id>/<result_form_id>/<filename>.

    `instance.result_form_id` is required, so the result form must exist
    before the image is attached.
    """
    return (
        f"form_images/{instance.tally_id}/"
        f"{instance.result_form_id}/{filename}"
    )


class ResultFormImage(BaseModel):
    """An image attached to a result form, regardless of how it arrived.

    A single home for every image applied to a form. `source` records how
    the image got here (a manual upload or a PVP bundle import); when it
    came from a bundle, `pvp_submission` links back to that submission for
    provenance. The raw image source of truth remains the retained bundle
    zip on `PvpUploadBundle.zip_file`.
    """

    class Meta:
        app_label = "tally"
        # Deterministic gallery + export order (no implicit DB ordering).
        ordering = ["created_date", "id"]

    tally = models.ForeignKey(Tally, on_delete=models.PROTECT)
    result_form = models.ForeignKey(
        ResultForm,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=result_form_image_upload_to)
    # Pillow format ("JPEG"/"PNG") recorded when the bytes were verified
    # at ingest, so the serve view can declare a content type without
    # re-decoding or trusting the filename extension.
    image_format = models.CharField(max_length=8, blank=True, default="")
    source = EnumIntegerField(
        ResultFormImageSource, default=ResultFormImageSource.UPLOAD,
    )
    kind = EnumIntegerField(
        ResultFormImageKind, default=ResultFormImageKind.SUPPORTING,
    )
    caption = models.CharField(max_length=255, null=True, blank=True)
    # Soft-delete flag. reset_to_unsubmitted deactivates PVP-sourced
    # images rather than deleting them, mirroring how every other related
    # record is handled on reset and preserving the audit trail. Display
    # and export count only active images.
    active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        UserProfile, null=True, blank=True, on_delete=models.SET_NULL,
    )
    # Provenance link when source == PVP_IMPORT; null for manual uploads.
    pvp_submission = models.ForeignKey(
        PvpSubmission,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applied_images",
    )

    def __str__(self):
        return f"ResultFormImage({self.id}, {self.result_form_id})"
