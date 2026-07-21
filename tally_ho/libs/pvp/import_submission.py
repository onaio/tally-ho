"""Per-submission PVP import.

Behavior depends on ``bundle.mode``:

- ``DE1_ONLY``: round2 is written as a single ``DATA_ENTRY_1`` set of
  ``Result`` rows + a DE1 ``ReconciliationForm``; the form transitions
  ``UNSUBMITTED`` -> ``DATA_ENTRY_2`` for a human clerk to enter DE2.
- ``DE1_AND_DE2``: round1 -> DE1 ``Result`` rows + DE1 ``ReconciliationForm``,
  round2 -> DE2 ``Result`` rows + DE2 ``ReconciliationForm``. The form
  transitions ``UNSUBMITTED`` -> ``QUALITY_CONTROL`` (the device already
  guarantees round1 == round2, so corrections is a no-op gate we skip).

Image extraction from the bundle zip is deferred to a
``transaction.on_commit`` callback so a rollback leaves nothing on disk.

Caller responsibilities:
- Pre-validate the row via ``tally_ho.libs.pvp.validation.validate_row``.
  This function assumes the form is eligible (UNSUBMITTED, not previously
  imported, barcode resolves in this tally).
- Pass the bundle's open ``zipfile.ZipFile`` as ``zip_ref``; this module
  reads ``media/<filename>`` entries from it during the on_commit pass.
"""

from __future__ import annotations

import logging
import zipfile
import zlib

import reversion
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_image import ResultFormImage
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.models.enums.result_form_image_kind import (
    ResultFormImageKind,
)
from tally_ho.libs.models.enums.result_form_image_source import (
    ResultFormImageSource,
)
from tally_ho.libs.pvp.bundle import MAX_MEDIA_BYTES
from tally_ho.libs.utils.image_validation import validate_image_bytes

logger = logging.getLogger(__name__)

# Bundle image key -> the kind recorded on the applied ResultFormImage.
_IMAGE_KIND_BY_KEY = {
    "clerk_signature": ResultFormImageKind.CLERK_SIGNATURE,
    "forms_picture_1st_page": ResultFormImageKind.FORM_PAGE_1,
    "forms_picture_2nd_page": ResultFormImageKind.FORM_PAGE_2,
}

_RECON_FIELD_MAP_R2 = {
    "number_of_voter_cards_in_the_ballot_box":
        "reconciliation_r2-number_voter_cards_r2",
    "number_valid_votes":
        "reconciliation_r2-number_valid_ballots_r2",
    "number_invalid_votes":
        "reconciliation_r2-number_invalid_ballots_r2",
    "number_sorted_and_counted":
        "reconciliation_r2-number_ballots_inside_box_r2",
}
_RECON_FIELD_MAP_R1 = {
    "number_of_voter_cards_in_the_ballot_box":
        "reconciliation_r1-number_voter_cards_r1",
    "number_valid_votes":
        "reconciliation_r1-number_valid_ballots_r1",
    "number_invalid_votes":
        "reconciliation_r1-number_invalid_ballots_r1",
    "number_sorted_and_counted":
        "reconciliation_r1-number_ballots_inside_box_r1",
}


@transaction.atomic
def import_submission(
    parsed_submission, *, tally, bundle, uploaded_by, zip_ref,
):
    """Import one validated PVP submission.

    Entry-version writes depend on ``bundle.mode`` — see the module
    docstring for the DE1_ONLY vs DE1_AND_DE2 breakdown. Wraps the
    write pass in a reversion revision for audit history.
    """
    with reversion.create_revision():
        reversion.set_user(uploaded_by)
        reversion.set_comment(
            f"PVP import (bundle {bundle.id}, "
            f"instance {parsed_submission.odk_instance_id})"
        )
        context = _prepare_import(
            parsed_submission, tally=tally, bundle=bundle,
        )
        return _apply_import(
            parsed_submission,
            uploaded_by=uploaded_by,
            zip_ref=zip_ref,
            **context,
        )


def _prepare_import(parsed_submission, *, tally, bundle):
    """Resolve DB rows and pick the per-mode write plan.

    Read-only lookups plus the ``PvpSubmission`` provenance row, then
    dispatch on ``bundle.mode`` to select ``entries`` + ``next_state``.
    Returns a kwargs dict fed to ``_apply_import``.
    """
    result_form = ResultForm.objects.get(
        tally=tally, barcode=parsed_submission.barcode,
    )
    station = Station.objects.get(
        tally=tally,
        center=result_form.center,
        station_number=result_form.station_number,
    )

    submission = PvpSubmission.objects.create(
        tally=tally,
        bundle=bundle,
        odk_instance_id=parsed_submission.odk_instance_id,
        odk_form_id=parsed_submission.odk_form_id,
        barcode=parsed_submission.barcode,
        staff_user_name=parsed_submission.staff_user_name,
        round1_raw={
            c.candidate_id: c.round1
            for c in parsed_submission.candidates
        },
        round2_raw={
            c.candidate_id: c.round2
            for c in parsed_submission.candidates
        },
        recon_raw=dict(parsed_submission.recon),
    )

    # Pre-resolve candidates once for the whole submission.
    candidates_by_parsed = {
        pc: Candidate.objects.get(
            tally=tally,
            ballot=result_form.ballot,
            candidate_id=int(pc.candidate_id),
        )
        for pc in parsed_submission.candidates
    }

    entries, next_state = _entry_plan(bundle.mode)

    return {
        "tally": tally,
        "result_form": result_form,
        "station": station,
        "submission": submission,
        "candidates_by_parsed": candidates_by_parsed,
        "entries": entries,
        "next_state": next_state,
    }


def _entry_plan(mode):
    """Pick the (entries, next_state) tuple for ``bundle.mode``.

    ``entries`` is a tuple of
    ``(EntryVersion, round_getter, recon_map)`` triples. ``round_getter``
    is a callable of a ``CandidateResult`` returning the vote count
    for that entry version; callable form avoids ``getattr`` on a
    stringly-typed attribute name.
    """
    if mode == PvpMode.DE1_AND_DE2:
        # FINAL is created here (round2 values) because DE1_AND_DE2
        # skips corrections — which is what normally writes FINAL rows.
        # Without this, reports/exports that filter on EntryVersion.FINAL
        # would not see PVP-imported forms in this mode. round1 == round2
        # is guaranteed by the device, so FINAL is deterministic.
        entries = (
            (EntryVersion.DATA_ENTRY_1,
             lambda pc: pc.round1, _RECON_FIELD_MAP_R1),
            (EntryVersion.DATA_ENTRY_2,
             lambda pc: pc.round2, _RECON_FIELD_MAP_R2),
            (EntryVersion.FINAL,
             lambda pc: pc.round2, _RECON_FIELD_MAP_R2),
        )
        return entries, FormState.QUALITY_CONTROL
    if mode == PvpMode.DE1_ONLY:
        entries = (
            (EntryVersion.DATA_ENTRY_1,
             lambda pc: pc.round2, _RECON_FIELD_MAP_R2),
        )
        return entries, FormState.DATA_ENTRY_2
    raise ValueError(f"unsupported PVP mode {mode}")


def _apply_import(
    parsed_submission, *, tally, result_form, station, submission,
    candidates_by_parsed, entries, next_state, uploaded_by, zip_ref,
):
    """Write Result + ReconciliationForm rows, flip form state, save images.

    Assumes ``_prepare_import`` has already populated every kwarg. All
    parse-time guarantees hold here: recon keys are present (checked
    in ``bundle._check_required_columns``) and round values are
    non-null and equal (``bundle._check_round_integrity``).
    """
    recon = parsed_submission.recon
    for entry_version, get_round, recon_map in entries:
        for parsed_candidate, candidate in candidates_by_parsed.items():
            Result.objects.create(
                candidate=candidate,
                result_form=result_form,
                tally=tally,
                user=uploaded_by,
                entry_version=entry_version,
                votes=get_round(parsed_candidate),
                active=True,
            )
        ReconciliationForm.objects.create(
            result_form=result_form,
            tally=tally,
            user=uploaded_by,
            entry_version=entry_version,
            active=True,
            number_of_voters=station.registrants,
            number_of_voter_cards_in_the_ballot_box=recon[
                recon_map["number_of_voter_cards_in_the_ballot_box"]],
            number_valid_votes=recon[recon_map["number_valid_votes"]],
            number_invalid_votes=recon[
                recon_map["number_invalid_votes"]],
            number_sorted_and_counted=recon[
                recon_map["number_sorted_and_counted"]],
            ballot_number_from=None,
            ballot_number_to=None,
            notes=None,
        )

    result_form.previous_form_state = result_form.form_state
    result_form.form_state = next_state
    result_form.duplicate_reviewed = False
    result_form.user = uploaded_by
    result_form.pvp_submission = submission
    result_form.save()

    transaction.on_commit(
        lambda: _save_images(
            result_form_id=result_form.id,
            tally_id=tally.id,
            submission_id=submission.id,
            uploaded_by_id=uploaded_by.id,
            images=parsed_submission.images,
            zip_ref=zip_ref,
        ),
    )

    return submission


def import_bundle(*, bundle, submissions, tally, uploaded_by, zip_ref):
    """Import a list of validated submissions, flipping bundle status.

    Caller is expected to have already filtered out rows that fail
    parse-time validation. The bundle row already exists (created at
    upload time); this function walks the validated subset, calls
    `import_submission` for each row inside a single outer atomic
    transaction, and flips the bundle to COMPLETED on success.

    All-or-nothing: if any `import_submission` raises, the outer atomic
    rolls back every prior submission's writes (each row's own atomic
    becomes a savepoint of the outer). Image `on_commit` callbacks
    registered by successful submissions are discarded on rollback, so
    no orphan files land on disk. Callers are responsible for flipping
    the bundle to FAILED and persisting the exception message.
    """
    submissions = list(submissions)
    with transaction.atomic():
        for parsed in submissions:
            import_submission(
                parsed,
                tally=tally,
                bundle=bundle,
                uploaded_by=uploaded_by,
                zip_ref=zip_ref,
            )
        bundle.number_of_submissions = len(submissions)
        bundle.imported_at = timezone.now()
        bundle.status = PvpBundleStatus.COMPLETED
        bundle.save(update_fields=[
            "number_of_submissions", "imported_at",
            "status", "modified_date",
        ])
    return bundle


def _save_images(
    *, result_form_id, tally_id, submission_id, uploaded_by_id, images,
    zip_ref,
):
    """Create ResultFormImage rows after the import transaction commits.

    Each bundle image becomes one ``ResultFormImage`` with
    ``source=PVP_IMPORT`` linked back to the ``PvpSubmission`` for
    provenance. Failures here leave the form with fewer images; the
    import's DB writes are already committed. Rollbacks in the parent
    transaction cancel this callback before it ever fires.
    """
    for key, kind in _IMAGE_KIND_BY_KEY.items():
        _attach_image(
            result_form_id=result_form_id,
            tally_id=tally_id,
            submission_id=submission_id,
            uploaded_by_id=uploaded_by_id,
            kind=kind,
            filename=images.get(key),
            zip_ref=zip_ref,
        )


def _attach_image(
    *, result_form_id, tally_id, submission_id, uploaded_by_id, kind,
    filename, zip_ref,
):
    """Read one media entry from the zip and create a ResultFormImage.

    Returns True if a row was created, False otherwise. Any problem —
    missing filename, member absent from the zip, oversized, corrupt
    member, or bytes that don't validate as an image — is a no-op (no row
    created). These conditions were already surfaced to the operator on
    the confirmation screen (``ParsedBundle.missing_images`` /
    ``invalid_images``) and consented to, so skipping here is expected,
    not a silent data loss.
    """
    if not filename:
        return False
    member = f"media/{filename}"
    try:
        if zip_ref.getinfo(member).file_size > MAX_MEDIA_BYTES:
            logger.warning(
                "PVP bundle image %r exceeds size cap; skipping", filename,
            )
            return False
        data = zip_ref.read(member)
    except (KeyError, zipfile.BadZipFile, OSError, zlib.error):
        # Missing member or a corrupt/truncated deflate stream — skip
        # rather than letting it escape this post-commit callback.
        logger.warning(
            "PVP bundle image %r could not be read; skipping", filename,
        )
        return False
    try:
        image_format = validate_image_bytes(data)
    except ValidationError:
        logger.warning(
            "PVP bundle image %r failed image validation; skipping",
            filename,
        )
        return False
    image = ResultFormImage(
        tally_id=tally_id,
        result_form_id=result_form_id,
        source=ResultFormImageSource.PVP_IMPORT,
        kind=kind,
        image_format=image_format,
        pvp_submission_id=submission_id,
        uploaded_by_id=uploaded_by_id,
    )
    image.image.save(filename, ContentFile(data), save=True)
    return True
