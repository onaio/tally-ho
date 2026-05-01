"""Unit tests for the PVP parse-time validation rules.

The validation function is duck-typed — `tally` need only have a `pvp_mode`
attribute, and `result_form_by_barcode` is a dict of objects with
`form_state` and `pvp_submission_id` attributes. Tests use trivial
namedtuples as stand-ins for the real Django models, keeping the test
suite Django-free and fast.
"""

from collections import namedtuple

from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.pvp.bundle import (
    CandidateResult,
    ParsedSubmission,
)
from tally_ho.libs.pvp.validation import (
    REASON_ALREADY_IMPORTED,
    REASON_BARCODE_NOT_FOUND,
    REASON_FORM_NOT_UNSUBMITTED,
    REASON_PVP_DISABLED,
    REASON_REQUIRED_FIELDS,
    ValidationResult,
    validate_row,
)


_TallyStub = namedtuple("_TallyStub", ["pvp_mode"])
_ResultFormStub = namedtuple(
    "_ResultFormStub", ["form_state", "pvp_submission_id"],
)


def _submission(
    *,
    barcode="111",
    ballot_number="1313",
    instance_id="uuid:1",
    candidates=None,
):
    if candidates is None:
        candidates = (
            CandidateResult(candidate_id="c1", candidate_order=1,
                            round1=10, round2=12),
        )
    return ParsedSubmission(
        odk_instance_id=instance_id,
        odk_form_id="results_14065",
        barcode=barcode,
        ballot_number=ballot_number,
        staff_user_name="clerk",
        candidates=candidates,
        recon={},
        images={},
    )


def _tally(mode=PvpMode.DE1_ONLY):
    return _TallyStub(pvp_mode=mode)


def _form(state=FormState.UNSUBMITTED, pvp_submission_id=None):
    return _ResultFormStub(
        form_state=state, pvp_submission_id=pvp_submission_id,
    )


# ---- pvp_disabled --------------------------------------------------------


def test_pvp_disabled_fails_when_tally_mode_is_disabled():
    sub = _submission(barcode="111")
    result = validate_row(
        sub, _tally(PvpMode.DISABLED), {"111": _form()},
    )
    assert isinstance(result, ValidationResult)
    assert result.valid is False
    assert result.reason == REASON_PVP_DISABLED


def test_pvp_disabled_passes_when_tally_mode_is_de1_only():
    sub = _submission(barcode="111")
    result = validate_row(
        sub, _tally(PvpMode.DE1_ONLY), {"111": _form()},
    )
    assert result.valid is True
    assert result.reason is None


# ---- required_fields ----------------------------------------------------


def test_required_fields_fails_when_barcode_missing():
    sub = _submission(barcode="")
    result = validate_row(sub, _tally(), {})
    assert result.valid is False
    assert result.reason == REASON_REQUIRED_FIELDS


def test_required_fields_fails_when_ballot_number_missing():
    sub = _submission(ballot_number="")
    result = validate_row(sub, _tally(), {"111": _form()})
    assert result.valid is False
    assert result.reason == REASON_REQUIRED_FIELDS


def test_required_fields_fails_when_instance_id_missing():
    sub = _submission(instance_id="")
    result = validate_row(sub, _tally(), {"111": _form()})
    assert result.valid is False
    assert result.reason == REASON_REQUIRED_FIELDS


def test_required_fields_fails_when_no_candidate_has_round2():
    sub = _submission(candidates=(
        CandidateResult(candidate_id="c1", candidate_order=1,
                        round1=10, round2=None),
        CandidateResult(candidate_id="c2", candidate_order=2,
                        round1=5, round2=None),
    ))
    result = validate_row(sub, _tally(), {"111": _form()})
    assert result.valid is False
    assert result.reason == REASON_REQUIRED_FIELDS


def test_required_fields_passes_when_at_least_one_round2_present():
    sub = _submission(candidates=(
        CandidateResult(candidate_id="c1", candidate_order=1,
                        round1=10, round2=None),
        CandidateResult(candidate_id="c2", candidate_order=2,
                        round1=5, round2=5),
    ))
    result = validate_row(sub, _tally(), {"111": _form()})
    assert result.valid is True


# ---- barcode_in_tally ---------------------------------------------------


def test_barcode_not_found_when_lookup_dict_missing_barcode():
    sub = _submission(barcode="999")
    result = validate_row(sub, _tally(), {"111": _form()})
    assert result.valid is False
    assert result.reason == REASON_BARCODE_NOT_FOUND


def test_barcode_in_tally_passes_when_present():
    sub = _submission(barcode="111")
    result = validate_row(sub, _tally(), {"111": _form()})
    assert result.valid is True


# ---- form_unsubmitted ---------------------------------------------------


def test_form_not_unsubmitted_when_state_is_other():
    sub = _submission(barcode="111")
    result = validate_row(
        sub, _tally(),
        {"111": _form(state=FormState.DATA_ENTRY_1)},
    )
    assert result.valid is False
    assert result.reason == REASON_FORM_NOT_UNSUBMITTED


def test_form_unsubmitted_passes_when_state_is_unsubmitted():
    sub = _submission(barcode="111")
    result = validate_row(
        sub, _tally(), {"111": _form(state=FormState.UNSUBMITTED)},
    )
    assert result.valid is True


# ---- already_imported ---------------------------------------------------


def test_already_imported_when_pvp_submission_id_set():
    sub = _submission(barcode="111")
    result = validate_row(
        sub, _tally(),
        {"111": _form(pvp_submission_id=42)},
    )
    assert result.valid is False
    assert result.reason == REASON_ALREADY_IMPORTED


def test_not_already_imported_when_pvp_submission_id_is_none():
    sub = _submission(barcode="111")
    result = validate_row(
        sub, _tally(),
        {"111": _form(pvp_submission_id=None)},
    )
    assert result.valid is True


# ---- ordering: pvp_disabled wins over everything else --------------------


def test_pvp_disabled_short_circuits_other_checks():
    # All other checks would also fail, but pvp_disabled is reported first.
    sub = _submission(barcode="999", ballot_number="")
    result = validate_row(
        sub, _tally(PvpMode.DISABLED), {},
    )
    assert result.valid is False
    assert result.reason == REASON_PVP_DISABLED


def test_required_fields_checked_before_lookup():
    # Bad barcode AND missing ballot_number — required_fields wins.
    sub = _submission(barcode="999", ballot_number="")
    result = validate_row(sub, _tally(), {})
    assert result.valid is False
    assert result.reason == REASON_REQUIRED_FIELDS
