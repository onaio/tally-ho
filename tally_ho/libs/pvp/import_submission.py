"""Per-submission PVP import.

Writes ``EntryVersion.DATA_ENTRY_1`` ``Result`` rows + a DE1
``ReconciliationForm`` for one parsed submission, links the resulting
``PvpSubmission`` to its ``ResultForm``, and transitions the form's state
``UNSUBMITTED`` -> ``DATA_ENTRY_2``. Image extraction from the bundle zip
is deferred to a ``transaction.on_commit`` callback so a rollback leaves
nothing on disk.

Caller responsibilities:
- Pre-validate the row via ``tally_ho.libs.pvp.validation.validate_row``.
  This function assumes the form is eligible (UNSUBMITTED, not previously
  imported, barcode resolves in this tally).
- Pass the bundle's open ``zipfile.ZipFile`` as ``zip_ref``; this module
  reads ``media/<filename>`` entries from it during the on_commit pass.
"""

from __future__ import annotations

import reversion
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus

_RECON_FIELD_MAP = {
    "number_of_voter_cards_in_the_ballot_box":
        "reconciliation_r2-number_voter_cards_r2",
    "number_valid_votes":
        "reconciliation_r2-number_valid_ballots_r2",
    "number_invalid_votes":
        "reconciliation_r2-number_invalid_ballots_r2",
    "number_sorted_and_counted":
        "reconciliation_r2-number_ballots_inside_box_r2",
}


@transaction.atomic
def import_submission(
    parsed_submission, *, tally, bundle, uploaded_by, zip_ref,
):
    """Import one validated PVP submission as DE1 results + recon."""
    with reversion.create_revision():
        reversion.set_user(uploaded_by)
        reversion.set_comment(
            f"PVP import (bundle {bundle.id}, "
            f"instance {parsed_submission.odk_instance_id})"
        )
        return _import_submission_inner(
            parsed_submission, tally, bundle, uploaded_by, zip_ref,
        )


def _import_submission_inner(
    parsed_submission, tally, bundle, uploaded_by, zip_ref,
):
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

    for parsed_candidate in parsed_submission.candidates:
        candidate = Candidate.objects.get(
            tally=tally,
            ballot=result_form.ballot,
            candidate_id=int(parsed_candidate.candidate_id),
        )
        Result.objects.create(
            candidate=candidate,
            result_form=result_form,
            tally=tally,
            user=uploaded_by,
            entry_version=EntryVersion.DATA_ENTRY_1,
            votes=parsed_candidate.round2 or 0,
            active=True,
        )

    recon = parsed_submission.recon
    ReconciliationForm.objects.create(
        result_form=result_form,
        tally=tally,
        user=uploaded_by,
        entry_version=EntryVersion.DATA_ENTRY_1,
        active=True,
        number_of_voters=station.registrants,
        number_of_voter_cards_in_the_ballot_box=recon.get(
            _RECON_FIELD_MAP["number_of_voter_cards_in_the_ballot_box"]),
        number_valid_votes=recon.get(
            _RECON_FIELD_MAP["number_valid_votes"]),
        number_invalid_votes=recon.get(
            _RECON_FIELD_MAP["number_invalid_votes"]),
        number_sorted_and_counted=recon.get(
            _RECON_FIELD_MAP["number_sorted_and_counted"]),
        ballot_number_from=None,
        ballot_number_to=None,
        notes=None,
    )

    result_form.previous_form_state = result_form.form_state
    result_form.form_state = FormState.DATA_ENTRY_2
    result_form.duplicate_reviewed = False
    result_form.user = uploaded_by
    result_form.pvp_submission = submission
    result_form.save()

    transaction.on_commit(
        lambda: _save_images(submission.id, parsed_submission.images, zip_ref),
    )

    return submission


def import_bundle(*, bundle, submissions, tally, uploaded_by, zip_ref):
    """Import a list of validated submissions, flipping bundle status.

    Caller is expected to have already filtered out rows that fail
    parse-time validation. The bundle row already exists (created at
    upload time); this function walks the validated subset, calls
    `import_submission` for each row inside a single outer atomic
    transaction, and flips the bundle's terminal status.

    All-or-nothing: if any `import_submission` raises, the outer atomic
    rolls back every prior submission's writes (each row's own atomic
    becomes a savepoint of the outer). Image `on_commit` callbacks
    registered by successful submissions are discarded on rollback, so
    no orphan files land on disk. The bundle status flip to FAILED
    happens after the rollback so the FAILED row sticks.
    """
    submissions = list(submissions)
    try:
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
    except Exception:
        bundle.status = PvpBundleStatus.FAILED
        bundle.save(update_fields=["status", "modified_date"])
        raise
    return bundle


def _save_images(submission_id, images, zip_ref):
    """Save image FileFields after the import transaction commits.

    Failures here leave the affected fields null; the submission row
    itself is already committed. Rollbacks in the parent transaction
    cancel this callback before it ever fires.
    """
    submission = PvpSubmission.objects.get(id=submission_id)
    dirty = False
    for field_name, filename in images.items():
        if not filename:
            continue
        try:
            data = zip_ref.read(f"media/{filename}")
        except KeyError:
            continue  # missing image -> leave field null
        getattr(submission, field_name).save(
            filename, ContentFile(data), save=False,
        )
        dirty = True
    if dirty:
        submission.save()
