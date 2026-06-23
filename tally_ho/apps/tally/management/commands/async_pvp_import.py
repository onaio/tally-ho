"""Celery task that drives a PVP bundle import end-to-end.

Lives under ``apps.tally.management.commands.*`` so the routing config in
``settings/common.py`` automatically sends it to the ``tally_data_import``
Celery queue. Views call this via ``.delay()`` after the user confirms
the import on the confirmation screen.
"""

import zipfile

from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.celeryapp import app
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus
from tally_ho.libs.pvp.bundle import parse_bundle
from tally_ho.libs.pvp.import_submission import import_bundle
from tally_ho.libs.pvp.validation import validate_row


@app.task()
def async_pvp_import(bundle_id, user_id):
    """Parse, validate, and import a PVP upload bundle.

    Loads the bundle row created at upload time, flips its status to
    IMPORTING, parses the zip, filters rows through parse-time
    validation, and hands the validated subset to ``import_bundle``.
    The orchestrator flips status to COMPLETED on success or FAILED if
    anything raises.

    :param bundle_id: PvpUploadBundle.id
    :param user_id:   UserProfile.id (the super admin who confirmed)
    :returns:         the bundle id (round-trip for callers/monitoring)
    """
    bundle = PvpUploadBundle.objects.get(id=bundle_id)
    user = UserProfile.objects.get(id=user_id)

    bundle.status = PvpBundleStatus.IMPORTING
    bundle.save(update_fields=["status", "modified_date"])

    # Catch failures from parse/validation too — otherwise a corrupted
    # zip leaves the bundle stuck in IMPORTING. import_bundle handles
    # its own FAILED flip; this except covers everything before it.
    try:
        zip_path = bundle.zip_file.path
        parsed = parse_bundle(zip_path)

        barcodes = [s.barcode for s in parsed.rows]
        rf_by_barcode = {
            rf.barcode: rf
            for rf in ResultForm.objects.filter(
                tally=bundle.tally, barcode__in=barcodes,
            )
        }
        valid_submissions = [
            s for s in parsed.rows
            if validate_row(s, bundle.tally, rf_by_barcode).valid
        ]

        with zipfile.ZipFile(zip_path) as zip_ref:
            import_bundle(
                bundle=bundle,
                submissions=valid_submissions,
                tally=bundle.tally,
                uploaded_by=user,
                zip_ref=zip_ref,
            )
    except Exception as exc:
        bundle.refresh_from_db(fields=["status"])
        if bundle.status != PvpBundleStatus.FAILED:
            bundle.status = PvpBundleStatus.FAILED
        bundle.error_message = str(exc)
        bundle.save(
            update_fields=["status", "error_message", "modified_date"],
        )
        raise

    return bundle.id
