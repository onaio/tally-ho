from django.db import models

from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.base_model import BaseModel


class PvpSubmission(BaseModel):
    """One row per ODK submission that passed parse-time validation.

    PvpSubmission is a "phase 1: load" provenance record of the raw
    bundle payload. The link to the ResultForm it populated lives on
    `ResultForm.pvp_submission` only — not as a reverse FK here. Rows
    that fail parse-time validation are surfaced on the confirmation
    screen but never persisted.

    Images that arrived in the bundle are applied to the form as
    `ResultFormImage` rows (source=PVP_IMPORT) at import time, linked
    back here via `applied_images`; the raw image bytes remain available
    in the retained bundle zip on `PvpUploadBundle.zip_file`.
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

    # Raw payloads preserved for provenance and dupe/round handling.
    round1_raw = models.JSONField(default=dict, blank=True)
    round2_raw = models.JSONField(default=dict, blank=True)
    recon_raw = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"PvpSubmission({self.id}, {self.barcode})"
