from django.db import models
from enumfields import EnumIntegerField

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus
from tally_ho.libs.models.enums.pvp_mode import PvpMode


def bundle_zip_upload_to(instance, filename):
    """Path: pvp/bundles/<tally_id>/<bundle_id>/<filename>.

    `instance.id` is required, so callers must save the bundle (without the
    zip) once before attaching `zip_file` and saving again.
    """
    return f"pvp/bundles/{instance.tally_id}/{instance.id}/{filename}"


class PvpUploadBundle(BaseModel):
    """One row per zip upload of PVP results from ODK Central.

    Created at upload time with `status=PENDING`. The Celery import task
    flips status PENDING -> IMPORTING -> COMPLETED (or FAILED), populates
    `number_of_submissions`, and sets `imported_at`. The original zip is
    persisted via `zip_file` so it survives the gap between upload,
    confirmation, and async import.
    """

    class Meta:
        app_label = "tally"

    tally = models.ForeignKey(Tally, on_delete=models.PROTECT)
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT)
    filename = models.CharField(max_length=512)
    zip_file = models.FileField(
        upload_to=bundle_zip_upload_to, null=True, blank=True,
    )
    status = EnumIntegerField(
        PvpBundleStatus, default=PvpBundleStatus.PENDING,
    )
    # Snapshot of Tally.pvp_mode at upload time. Tally.pvp_mode itself
    # remains mutable; this field records what mode was actually applied
    # when the bundle was imported, so downstream consumers (exports,
    # audit, reporting) read the historical mode instead of the
    # current setting.
    mode = EnumIntegerField(PvpMode, default=PvpMode.DISABLED)
    number_of_submissions = models.PositiveIntegerField(default=0)
    imported_at = models.DateTimeField(null=True, blank=True)
    # Populated on FAILED with the exception that aborted the import,
    # so the result page can show the operator what went wrong instead
    # of a bare status flag.
    error_message = models.TextField(blank=True, default="")

    def __str__(self):
        return f"PvpUploadBundle({self.id}, {self.filename}, {self.status})"
