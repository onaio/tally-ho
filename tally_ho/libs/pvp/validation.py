"""Parse-time validation for PVP submission rows.

`validate_row` is duck-typed: `tally` need only have a `pvp_mode`, and
`result_form_by_barcode` is a dict keyed on barcode whose values have
`form_state` and `pvp_submission_id` attributes. This keeps the module
Django-free for fast unit tests; production callers pass real models.

Rows that fail validation are surfaced on the confirmation screen but
never persisted as PvpSubmission rows. Callers should pre-populate
`result_form_by_barcode` with a single bulk query to avoid N+1.
"""

from __future__ import annotations

from dataclasses import dataclass

from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_mode import PvpMode

# Reason codes shown on the confirmation screen's "will skip" list.
REASON_PVP_DISABLED = "pvp_disabled"
REASON_REQUIRED_FIELDS = "required_fields"
REASON_BARCODE_NOT_FOUND = "barcode_not_found"
REASON_FORM_NOT_UNSUBMITTED = "form_not_unsubmitted"
REASON_ALREADY_IMPORTED = "already_imported"


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str | None = None


def validate_row(submission, tally, result_form_by_barcode):
    """Apply parse-time validation to a single ParsedSubmission.

    Order matters: `pvp_disabled` is a tally-wide property and is reported
    first; subsequent checks short-circuit on the first failure so each
    row gets exactly one reason code.
    """
    if tally.pvp_mode == PvpMode.DISABLED:
        return ValidationResult(False, REASON_PVP_DISABLED)

    if not _has_required_fields(submission):
        return ValidationResult(False, REASON_REQUIRED_FIELDS)

    result_form = result_form_by_barcode.get(submission.barcode)
    if result_form is None:
        return ValidationResult(False, REASON_BARCODE_NOT_FOUND)

    if result_form.form_state != FormState.UNSUBMITTED:
        return ValidationResult(False, REASON_FORM_NOT_UNSUBMITTED)

    if result_form.pvp_submission_id is not None:
        return ValidationResult(False, REASON_ALREADY_IMPORTED)

    return ValidationResult(True, None)


def _has_required_fields(submission):
    return bool(
        submission.barcode
        and submission.ballot_number
        and submission.odk_instance_id
        and any(c.round2 is not None for c in submission.candidates)
    )
