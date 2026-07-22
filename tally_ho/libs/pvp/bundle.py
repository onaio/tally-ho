"""Pure-Python parser for PVP upload bundles emitted by odk-central-sync.

A bundle is a zip with:

    candidate_results.csv     # one row per (submission, candidate)
    media/<image-filename>... # signature + form pictures referenced by the CSV

The parser has no database dependency — callers (the upload view, the
celery import task) construct the parser inputs and consume its dataclass
output, and per-row validation against the database lives at a higher
layer. It does depend on Pillow and ``django.core.exceptions`` to verify
image bytes at parse time (see ``_find_invalid_images``); loading a file
is the obvious attack surface, so images are checked here before anything
downstream trusts them.
"""

from __future__ import annotations

import csv
import dataclasses
import io
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.image_validation import validate_image_bytes

CSV_NAME = "candidate_results.csv"
MEDIA_DIR = "media"

# Cap the decompressed size of a single media entry before reading it, so
# a maliciously crafted bundle (tiny compressed, huge inflated) cannot
# exhaust memory before the image is validated. Generous for a phone
# photo of a paper form.
MAX_MEDIA_BYTES = 25 * 1024 * 1024  # 25 MiB

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
    # Image filenames referenced by the CSV but absent from the zip.
    missing_images: list[str] = field(default_factory=list)
    # Image filenames present in the zip but not a valid JPEG/PNG/WebP
    # (or exceeding the size cap). Surfaced on the confirmation screen
    # like missing images; the operator proceeds with informed consent
    # and the affected slot produces no ResultFormImage row.
    invalid_images: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.rows)


def parse_bundle(zip_path: str | Path) -> ParsedBundle:
    """Parse a PVP upload bundle into submission-level rows.

    Raises:
      InvalidBundleError: zip can't open, csv missing, required columns
        gone, or a value that must parse as an integer doesn't
      DuplicateBarcodeError: same barcode appears in more than one
        submission
      RoundIntegrityError: any candidate row has missing rounds or
        round1 != round2 (device guarantees they match)
      UnsafeImageFilenameError: an image filename contains path syntax
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

        parsed = _build_parsed_bundle(csv_rows, media_filenames)
        invalid_images = _find_invalid_images(
            archive, parsed.rows, media_filenames,
        )

    return dataclasses.replace(parsed, invalid_images=invalid_images)


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
        # All accessed columns are in REQUIRED_COLUMNS so a KeyError here
        # would mean the upstream column check was bypassed or DictReader
        # behaved unexpectedly. Wrap it as InvalidBundleError so the
        # operator sees a meaningful message instead of a raw traceback.
        try:
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
                col: _safe_image_filename(first[col])
                for col in IMAGE_COLUMNS
            }
            submission = ParsedSubmission(
                odk_instance_id=instance_id,
                odk_form_id=first["xml_form_id"],
                barcode=first["barcode"],
                ballot_number=first["ballot_number"],
                staff_user_name=first["staff_user_name"] or None,
                candidates=candidates,
                recon=recon,
                images=images,
            )
        except KeyError as exc:
            raise InvalidBundleError(
                _("row missing required column: %(column)s") % {
                    "column": exc.args[0],
                }
            ) from exc
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


def _find_invalid_images(archive, submissions, media_filenames):
    """Return the sorted filenames that are present in the zip but are not
    a valid image (or exceed the size cap).

    Reads each present, referenced image once and runs it through Pillow
    verification. Oversized entries are treated as invalid without being
    read into memory. Missing images (referenced but absent from the zip)
    are handled separately by ``missing_images`` and are not re-reported
    here.
    """
    referenced = {
        name
        for submission in submissions
        for name in submission.images.values()
        if name
    }
    invalid = set()
    for name in referenced & media_filenames:
        member = f"{MEDIA_DIR}/{name}"
        if archive.getinfo(member).file_size > MAX_MEDIA_BYTES:
            invalid.add(name)
            continue
        try:
            validate_image_bytes(archive.read(member))
        except (ValidationError, zipfile.BadZipFile, zlib.error, OSError):
            # Not a valid image, or a corrupt/truncated member whose
            # read fails — classify as invalid (surfaced on the
            # confirmation screen) rather than escaping parse_bundle.
            # Mirrors the except set in import_submission._attach_image.
            invalid.add(name)
    return sorted(invalid)


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
