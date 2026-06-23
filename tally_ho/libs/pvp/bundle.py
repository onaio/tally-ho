"""Pure-Python parser for PVP upload bundles emitted by odk-central-sync.

A bundle is a zip with:

    candidate_results.csv     # one row per (submission, candidate)
    media/<image-filename>... # signature + form pictures referenced by the CSV

This module is intentionally Django-free: callers (the upload view, the
celery import task) construct the parser inputs and consume its dataclass
output. Parse-time validation lives at a higher layer (per-row checks
against the database).
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from django.utils.translation import gettext_lazy as _

CSV_NAME = "candidate_results.csv"
MEDIA_DIR = "media"

# Recon fields we preserve verbatim into PvpSubmission.recon_raw.
RECON_COLUMNS = (
    "reconciliation_r1-number_ballots_received_r1",
    "reconciliation_r1-number_voter_cards_r1",
    "reconciliation_r1-number_valid_ballots_r1",
    "reconciliation_r1-number_invalid_ballots_r1",
    "reconciliation_r1-number_ballots_inside_box_r1",
    "reconciliation_r2-number_ballots_received_r2",
    "reconciliation_r2-number_voter_cards_r2",
    "reconciliation_r2-number_valid_ballots_r2",
    "reconciliation_r2-number_invalid_ballots_r2",
    "reconciliation_r2-number_ballots_inside_box_r2",
)

# Columns we use during parsing. If any are missing, raise InvalidBundleError.
# All RECON_COLUMNS are required: DE1_AND_DE2 mode reads the r1 fields, and
# even in DE1_ONLY we preserve them in PvpSubmission.recon_raw for audit.
REQUIRED_COLUMNS = (
    "meta-instanceID",
    "barcode",
    "ballot_number",
    "candidate_id",
    "candidate_order",
    "candidate_result_round1",
    "candidate_result_round2",
    "xml_form_id",
    "staff_user_name",
    *RECON_COLUMNS,
    "clerk_signature",
    "forms_picture_1st_page",
    "forms_picture_2nd_page",
)

IMAGE_COLUMNS = (
    "clerk_signature",
    "forms_picture_1st_page",
    "forms_picture_2nd_page",
)


class InvalidBundleError(Exception):
    """Bundle is structurally broken (missing CSV, missing columns)."""


class DuplicateBarcodeError(Exception):
    """More than one submission row references the same barcode."""


class RoundIntegrityError(Exception):
    """A row has missing rounds or a round1 != round2 mismatch.

    The device's whole purpose is double-entry validation: both rounds
    should be present and equal in every emitted submission. Any
    departure signals data corruption between device and tally — fail
    the whole bundle so the operator investigates.
    """


class UnsafeImageFilenameError(Exception):
    """An image filename contains path syntax (separator or ``..``).

    Device-emitted filenames are bare basenames; anything path-shaped
    signals a hand-crafted or corrupted bundle. Surface it so the
    operator investigates rather than silently dropping the image.
    """


@dataclass(frozen=True)
class CandidateResult:
    candidate_id: str
    candidate_order: int
    round1: int | None
    round2: int | None


@dataclass(frozen=True)
class ParsedSubmission:
    odk_instance_id: str
    odk_form_id: str
    barcode: str
    ballot_number: str
    staff_user_name: str | None
    candidates: tuple[CandidateResult, ...]
    recon: dict[str, int | None]
    images: dict[str, str | None]


@dataclass(frozen=True)
class ParsedBundle:
    rows: tuple[ParsedSubmission, ...]
    missing_images: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.rows)


def parse_bundle(zip_path: str | Path) -> ParsedBundle:
    """Parse a PVP upload bundle into submission-level rows.

    Raises:
      InvalidBundleError: zip can't open, csv missing, required columns gone
      DuplicateBarcodeError: same barcode appears in more than one submission
    """
    path = Path(zip_path)
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise InvalidBundleError(
            _("could not open zip: %(error)s") % {"error": exc}
        ) from exc

    with archive:
        if CSV_NAME not in archive.namelist():
            raise InvalidBundleError(
                _("bundle is missing %(name)s") % {"name": CSV_NAME}
            )
        media_filenames = {
            name[len(MEDIA_DIR) + 1:]
            for name in archive.namelist()
            if name.startswith(MEDIA_DIR + "/") and not name.endswith("/")
        }
        with archive.open(CSV_NAME) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text)
            _check_required_columns(reader.fieldnames or [])
            csv_rows = list(reader)

    return _build_parsed_bundle(csv_rows, media_filenames)


def _check_required_columns(fieldnames):
    present = set(fieldnames)
    missing = [column for column in REQUIRED_COLUMNS if column not in present]
    if missing:
        raise InvalidBundleError(
            _("bundle CSV is missing required columns: %(columns)s") % {
                "columns": ", ".join(missing),
            }
        )


def _build_parsed_bundle(csv_rows, media_filenames):
    by_instance: dict[str, list[dict]] = {}
    for row in csv_rows:
        instance_id = row["meta-instanceID"]
        if not instance_id:
            continue
        by_instance.setdefault(instance_id, []).append(row)

    submissions: list[ParsedSubmission] = []
    barcode_to_instances: dict[str, list[str]] = {}

    for instance_id, group in by_instance.items():
        first = group[0]
        candidates = tuple(
            CandidateResult(
                candidate_id=row["candidate_id"],
                candidate_order=_to_int(row["candidate_order"]) or 0,
                round1=_to_int(row["candidate_result_round1"]),
                round2=_to_int(row["candidate_result_round2"]),
            )
            for row in group
        )
        recon = {col: _to_int(first[col]) for col in RECON_COLUMNS}
        images = {
            col: _safe_image_filename(first.get(col))
            for col in IMAGE_COLUMNS
        }
        submission = ParsedSubmission(
            odk_instance_id=instance_id,
            odk_form_id=first.get("xml_form_id", ""),
            barcode=first["barcode"],
            ballot_number=first.get("ballot_number", ""),
            staff_user_name=first.get("staff_user_name") or None,
            candidates=candidates,
            recon=recon,
            images=images,
        )
        submissions.append(submission)
        barcode_to_instances.setdefault(submission.barcode, []).append(
            instance_id,
        )

    duplicates = {
        barcode: instances
        for barcode, instances in barcode_to_instances.items()
        if len(instances) > 1
    }
    if duplicates:
        listing = ", ".join(sorted(duplicates))
        raise DuplicateBarcodeError(
            _("barcodes appear in more than one submission: %(barcodes)s") % {
                "barcodes": listing,
            }
        )

    _check_round_integrity(submissions)

    referenced_images = {
        name
        for submission in submissions
        for name in submission.images.values()
        if name
    }
    missing_images = sorted(referenced_images - media_filenames)

    return ParsedBundle(
        rows=tuple(submissions),
        missing_images=missing_images,
    )


def _check_round_integrity(submissions):
    offenders = []
    for submission in submissions:
        for candidate in submission.candidates:
            if (
                candidate.round1 is None
                or candidate.round2 is None
                or candidate.round1 != candidate.round2
            ):
                offenders.append(submission.barcode)
                break
    if offenders:
        listing = ", ".join(sorted(set(offenders)))
        raise RoundIntegrityError(
            _("barcodes with missing or mismatched rounds: %(barcodes)s") % {
                "barcodes": listing,
            }
        )


def _safe_image_filename(value):
    """Validate an image filename is a bare basename.

    Django's storage (FileSystemStorage + safe_join) already prevents
    writes outside MEDIA_ROOT, but a crafted filename like
    ``../{other}/img.jpg`` still resolves *inside* MEDIA_ROOT to a
    different submission's directory and can overwrite another
    submission's image. Surface anything with path syntax loudly so
    the operator sees the bad bundle.
    """
    if not value:
        return None
    if "/" in value or "\\" in value or ".." in value:
        raise UnsafeImageFilenameError(
            _("image filename contains path syntax: %(name)r") % {
                "name": value,
            }
        )
    return value


def _to_int(value):
    """Parse a numeric column value; empty stays None, garbage raises.

    Empty/None is a legitimate "no value" for optional ints (e.g. an
    unrecorded round). A non-int string like ``"abc"`` signals upstream
    corruption — surface it rather than silently dropping data.
    """
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidBundleError(
            _("expected integer, got %(value)r") % {"value": value}
        ) from exc
