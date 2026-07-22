"""Unit tests for the PVP bundle parser.

Pure-Python tests against an in-memory zip — no Django, no fixtures on disk.
The parser is intentionally Django-free; these tests run without a DB.
"""

import csv
import io
import zipfile
import zlib

import pytest
from PIL import Image

from tally_ho.libs.pvp.bundle import (
    DuplicateBarcodeError,
    InvalidBundleError,
    ParsedBundle,
    ParsedSubmission,
    RoundIntegrityError,
    UnsafeImageFilenameError,
    _find_invalid_images,
    parse_bundle,
)


def _real_jpeg(size=(4, 4)):
    """Genuine JPEG bytes — the parser now Pillow-validates every present
    image, so fixtures must be real images unless testing the invalid path.
    """
    buf = io.BytesIO()
    Image.new("RGB", size).save(buf, format="JPEG")
    return buf.getvalue()


# Headers that the post-Task-1 odk-central-sync emits in the bundle CSV.
HEADERS = [
    "pos",
    "candidate_id",
    "candidate_order",
    "candidate_name",
    "candidate_result_round1",
    "candidate_result_round2",
    "meta-instanceID",
    "KEY",
    "xml_form_id",
    "center_id",
    "station_number",
    "staff_user_name",
    "ballot_number",
    "race_type",
    "barcode",
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
    "clerk_signature",
    "forms_picture_1st_page",
    "forms_picture_2nd_page",
]


def _candidate_row(
    *,
    instance_id,
    barcode,
    candidate_id,
    candidate_order,
    round1,
    round2,
    xml_form_id="results_14065",
    ballot_number="1313",
    staff_user_name="clerk",
    clerk_signature="14065_sig.jpg",
    page1="14065_p1.jpg",
    page2="",
):
    return {
        "pos": str(candidate_order),
        "candidate_id": str(candidate_id),
        "candidate_order": str(candidate_order),
        "candidate_name": f"Candidate {candidate_id}",
        "candidate_result_round1": str(round1) if round1 is not None else "",
        "candidate_result_round2": str(round2) if round2 is not None else "",
        "meta-instanceID": instance_id,
        "KEY": f"{instance_id}/candidate_results[{candidate_order}]",
        "xml_form_id": xml_form_id,
        "center_id": "14065",
        "station_number": "3",
        "staff_user_name": staff_user_name,
        "ballot_number": ballot_number,
        "race_type": "Individual",
        "barcode": str(barcode),
        "reconciliation_r1-number_ballots_received_r1": "300",
        "reconciliation_r1-number_voter_cards_r1": "120",
        "reconciliation_r1-number_valid_ballots_r1": "118",
        "reconciliation_r1-number_invalid_ballots_r1": "2",
        "reconciliation_r1-number_ballots_inside_box_r1": "120",
        "reconciliation_r2-number_ballots_received_r2": "300",
        "reconciliation_r2-number_voter_cards_r2": "120",
        "reconciliation_r2-number_valid_ballots_r2": "118",
        "reconciliation_r2-number_invalid_ballots_r2": "2",
        "reconciliation_r2-number_ballots_inside_box_r2": "120",
        "clerk_signature": clerk_signature,
        "forms_picture_1st_page": page1,
        "forms_picture_2nd_page": page2,
    }


def _make_bundle(rows, *, image_filenames=None, headers=None,
                 include_csv=True, csv_name="candidate_results.csv",
                 bad_images=None, image_content=None):
    """Build a zip in-memory and return a Path-like to it (BytesIO).

    ``bad_images`` names media entries to write as non-image bytes (to
    exercise the invalid-image path). ``image_content`` optionally maps a
    filename to explicit bytes (e.g. an oversized entry).
    """
    headers = headers if headers is not None else HEADERS
    image_filenames = image_filenames or set()
    bad_images = bad_images or set()
    image_content = image_content or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        if include_csv:
            csv_buf = io.StringIO()
            writer = csv.DictWriter(csv_buf, fieldnames=headers,
                                    extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            zf.writestr(csv_name, csv_buf.getvalue())
        for name in image_filenames:
            if name in image_content:
                content = image_content[name]
            elif name in bad_images:
                content = b"not-an-image"
            else:
                content = _real_jpeg()
            zf.writestr(f"media/{name}", content)
    buf.seek(0)
    return buf


def _bundle_path(tmp_path, rows, **kwargs):
    """Persist a constructed bundle to disk and return the Path."""
    buf = _make_bundle(rows, **kwargs)
    p = tmp_path / "bundle.zip"
    p.write_bytes(buf.getvalue())
    return p


# ---- happy path -----------------------------------------------------------


def test_valid_bundle_returns_parsed_bundle(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=12, round2=12),
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c2", candidate_order=2,
                       round1=22, round2=22),
        _candidate_row(instance_id="uuid:s2", barcode="222",
                       candidate_id="c1", candidate_order=1,
                       round1=5, round2=5,
                       clerk_signature="14065_sig2.jpg",
                       page1="14065_p1b.jpg"),
    ]
    path = _bundle_path(
        tmp_path, rows,
        image_filenames={"14065_sig.jpg", "14065_p1.jpg",
                         "14065_sig2.jpg", "14065_p1b.jpg"},
    )

    parsed = parse_bundle(path)

    assert isinstance(parsed, ParsedBundle)
    assert parsed.total == 2  # two unique submissions
    assert len(parsed.rows) == 2
    assert parsed.missing_images == []

    by_id = {s.odk_instance_id: s for s in parsed.rows}
    s1 = by_id["uuid:s1"]
    assert s1.barcode == "111"
    assert s1.odk_form_id == "results_14065"
    assert s1.staff_user_name == "clerk"
    assert len(s1.candidates) == 2
    cands = sorted(s1.candidates, key=lambda c: c.candidate_order)
    assert cands[0].candidate_id == "c1"
    assert cands[0].round1 == 12
    assert cands[0].round2 == 12
    assert cands[1].round2 == 22

    # Recon: r1 + r2 fields are preserved verbatim with the source key names.
    assert s1.recon["reconciliation_r2-number_valid_ballots_r2"] == 118
    assert s1.recon["reconciliation_r1-number_ballots_received_r1"] == 300

    # Images: filename or None per the three image columns.
    assert s1.images["clerk_signature"] == "14065_sig.jpg"
    assert s1.images["forms_picture_1st_page"] == "14065_p1.jpg"
    assert s1.images["forms_picture_2nd_page"] is None  # blank in fixture


# ---- error: missing csv ---------------------------------------------------


def test_missing_csv_raises_invalid_bundle(tmp_path):
    path = _bundle_path(tmp_path, rows=[], include_csv=False)
    with pytest.raises(InvalidBundleError, match="candidate_results.csv"):
        parse_bundle(path)


# ---- error: missing required columns -------------------------------------


def test_missing_required_columns_raises_invalid_bundle(tmp_path):
    truncated_headers = [
        h for h in HEADERS if h != "barcode"
    ]
    row = _candidate_row(instance_id="uuid:x", barcode="999",
                         candidate_id="c1", candidate_order=1,
                         round1=1, round2=1)
    path = _bundle_path(tmp_path, [row], headers=truncated_headers)
    with pytest.raises(InvalidBundleError, match="barcode"):
        parse_bundle(path)


# ---- warning: missing images (does not raise) ----------------------------


def test_missing_images_collected_not_raised(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="present.jpg",
                       page1="missing.jpg",
                       page2="also_missing.jpg"),
    ]
    path = _bundle_path(tmp_path, rows,
                        image_filenames={"present.jpg"})

    parsed = parse_bundle(path)

    assert parsed.total == 1
    assert sorted(parsed.missing_images) == [
        "also_missing.jpg", "missing.jpg",
    ]
    assert parsed.invalid_images == []


# ---- warning: invalid images (does not raise) ----------------------------


def test_invalid_images_collected_not_raised(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="good.jpg",
                       page1="corrupt.jpg",
                       page2="missing.jpg"),
    ]
    path = _bundle_path(
        tmp_path, rows,
        image_filenames={"good.jpg", "corrupt.jpg"},
        bad_images={"corrupt.jpg"},
    )

    parsed = parse_bundle(path)

    assert parsed.total == 1  # bundle still parses; not raised
    assert parsed.invalid_images == ["corrupt.jpg"]
    assert parsed.missing_images == ["missing.jpg"]


def test_valid_images_produce_no_invalid_entries(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="good.jpg"),
    ]
    path = _bundle_path(tmp_path, rows, image_filenames={"good.jpg"})

    parsed = parse_bundle(path)

    assert parsed.invalid_images == []


def test_corrupt_member_read_error_classified_invalid_not_raised():
    # A member whose read raises (corrupt deflate stream) is classified
    # as invalid rather than escaping the parser, mirroring the import.
    submission = ParsedSubmission(
        odk_instance_id="uuid:s1", odk_form_id="f", barcode="111",
        ballot_number="1", staff_user_name=None, candidates=(),
        recon={}, images={"clerk_signature": "bad.jpg"},
    )

    class _FakeInfo:
        file_size = 10  # under the cap, so it attempts a read

    class _FakeArchive:
        def getinfo(self, member):
            return _FakeInfo()

        def read(self, member):
            raise zlib.error("corrupt deflate stream")

    invalid = _find_invalid_images(
        _FakeArchive(), [submission], {"bad.jpg"},
    )
    assert invalid == ["bad.jpg"]


def test_oversized_image_is_invalid_without_reading(tmp_path):
    # An entry whose declared size exceeds the cap is invalid and must
    # not be read into memory. A ~30 MiB entry trips the 25 MiB cap.
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="huge.jpg"),
    ]
    path = _bundle_path(
        tmp_path, rows,
        image_filenames={"huge.jpg"},
        image_content={"huge.jpg": b"\x00" * (30 * 1024 * 1024)},
    )

    parsed = parse_bundle(path)

    assert parsed.invalid_images == ["huge.jpg"]


# ---- error: duplicate barcode within bundle ------------------------------


def test_duplicate_barcode_raises(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="DUP",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1),
        _candidate_row(instance_id="uuid:s2", barcode="DUP",
                       candidate_id="c1", candidate_order=1,
                       round1=2, round2=2),
    ]
    path = _bundle_path(tmp_path, rows)
    with pytest.raises(DuplicateBarcodeError, match="DUP"):
        parse_bundle(path)


# ---- round integrity -----------------------------------------------------


def test_missing_round1_raises_round_integrity(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=None, round2=10),
    ]
    path = _bundle_path(tmp_path, rows)
    with pytest.raises(RoundIntegrityError, match="111"):
        parse_bundle(path)


def test_missing_round2_raises_round_integrity(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=10, round2=None),
    ]
    path = _bundle_path(tmp_path, rows)
    with pytest.raises(RoundIntegrityError, match="111"):
        parse_bundle(path)


def test_round1_not_equal_round2_raises_round_integrity(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=10, round2=11),
    ]
    path = _bundle_path(tmp_path, rows)
    with pytest.raises(RoundIntegrityError, match="111"):
        parse_bundle(path)


def test_rounds_zero_zero_is_valid(tmp_path):
    # Zero votes is a legitimate outcome; both rounds at zero must match.
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=0, round2=0),
    ]
    path = _bundle_path(tmp_path, rows,
                        image_filenames={"14065_sig.jpg", "14065_p1.jpg"})
    parsed = parse_bundle(path)
    assert parsed.total == 1


# ---- image filename safety -----------------------------------------------


def test_garbage_integer_value_raises_invalid_bundle(tmp_path):
    # candidate_order is parsed as int; "abc" is not.
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order="abc",
                       round1=1, round2=1),
    ]
    with pytest.raises(InvalidBundleError, match="expected integer"):
        parse_bundle(_bundle_path(tmp_path, rows))


def test_image_filename_with_path_separator_raises(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="../../../etc/passwd"),
    ]
    path = _bundle_path(tmp_path, rows)
    with pytest.raises(UnsafeImageFilenameError, match="etc/passwd"):
        parse_bundle(path)


def test_image_filename_with_backslash_raises(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="..\\windows\\system32"),
    ]
    with pytest.raises(UnsafeImageFilenameError):
        parse_bundle(_bundle_path(tmp_path, rows))


# ---- accepts pathlib.Path or str -----------------------------------------


def test_accepts_str_path(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1),
    ]
    path = _bundle_path(tmp_path, rows,
                        image_filenames={"14065_sig.jpg", "14065_p1.jpg"})
    # Pass as a plain string, not Path.
    parsed = parse_bundle(str(path))
    assert isinstance(parsed, ParsedBundle)
    assert parsed.total == 1
