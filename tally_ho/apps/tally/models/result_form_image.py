import posixpath

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

IMAGE_UPLOAD_DIR = "form_images"


def build_result_form_image_path(tally_id, result_form_id, filename):
    """Path: form_images/<tally_id>/<result_form_id>/<basename>.

    Deliberately not an ``upload_to`` callable, so the migration graph
    never pins it (see AGENTS.md). ``filename`` is untrusted and may use
    either separator; no directory prefix survives.
    """
    return posixpath.join(
        IMAGE_UPLOAD_DIR,
        str(tally_id),
        str(result_form_id),
        posixpath.basename(filename.replace("\\", "/")),
    )


class ResultFormImage(BaseModel):
    """An image attached to a result form, regardless of how it arrived.

    ``active`` is a soft-delete flag; display and exports count only
    active images. The raw image source of truth remains the retained
    bundle zip on `PvpUploadBundle.zip_file`.
    """

    class Meta:
        app_label = "tally"
        ordering = ["created_date", "id"]
        indexes = [
            models.Index(fields=["result_form", "active"]),
        ]

    tally = models.ForeignKey(Tally, on_delete=models.PROTECT)
    result_form = models.ForeignKey(
        ResultForm,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField()
    image_format = models.CharField(max_length=8, blank=True, default="")
    source = EnumIntegerField(
        ResultFormImageSource, default=ResultFormImageSource.UPLOAD,
    )
    kind = EnumIntegerField(
        ResultFormImageKind, default=ResultFormImageKind.SUPPORTING,
    )
    caption = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        UserProfile, null=True, blank=True, on_delete=models.SET_NULL,
    )
    pvp_submission = models.ForeignKey(
        PvpSubmission,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applied_images",
    )

    def save(self, *args, **kwargs):
        """Repath an unstored file, in place of an ``upload_to`` callable
        the migration graph would pin forever (see AGENTS.md).
        """
        if self.image and not self.image._committed:
            self.image.name = build_result_form_image_path(
                self.tally_id, self.result_form_id, self.image.name,
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"ResultFormImage({self.id}, {self.result_form_id})"
