from django.db import models

from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.base_model import BaseModel


def submission_image_upload_to(instance, filename):
    """Path: pvp/<tally_id>/<submission_id>/<filename>.

    `instance.id` is required, so callers must save the submission (without
    image fields) once before attaching files and saving again.
    """
    return f"pvp/{instance.tally_id}/{instance.id}/{filename}"


class PvpSubmission(BaseModel):
    """One row per ODK submission that passed parse-time validation.

    PvpSubmission is a "phase 1: load" provenance record. The link to the
    ResultForm it populated lives on `ResultForm.pvp_submission` only —
    not as a reverse FK here. Rows that fail parse-time validation are
    surfaced on the confirmation screen but never persisted.
    """

    class Meta:
        app_label = "tally"
        unique_together = (("tally", "odk_instance_id"),)

    tally = models.ForeignKey(Tally, on_delete=models.PROTECT)
    bundle = models.ForeignKey(
        PvpUploadBundle,
        on_delete=models.PROTECT,
        related_name="submissions",
    )

    odk_instance_id = models.CharField(max_length=255)
    odk_form_id = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255)
    staff_user_name = models.CharField(max_length=255, null=True, blank=True)
    submission_date = models.DateTimeField(null=True, blank=True)

    # Raw payloads kept for provenance + future pass-2 dupe/round handling.
    round1_raw = models.JSONField(default=dict, blank=True)
    round2_raw = models.JSONField(default=dict, blank=True)
    recon_raw = models.JSONField(default=dict, blank=True)

    # Images stored under MEDIA_ROOT/pvp/<tally_id>/<submission_id>/.
    clerk_signature = models.FileField(
        upload_to=submission_image_upload_to, null=True, blank=True,
    )
    forms_picture_1st_page = models.FileField(
        upload_to=submission_image_upload_to, null=True, blank=True,
    )
    forms_picture_2nd_page = models.FileField(
        upload_to=submission_image_upload_to, null=True, blank=True,
    )

    def __str__(self):
        return f"PvpSubmission({self.id}, {self.barcode})"
