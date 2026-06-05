"""Unit tests for the PVP bundle parser.

Pure-Python tests against an in-memory zip — no Django, no fixtures on disk.
The parser is intentionally Django-free; these tests run without a DB.
"""

import csv
import io
import zipfile

import pytest

from tally_ho.libs.pvp.bundle import (
    DuplicateBarcodeError,
    InvalidBundleError,
    ParsedBundle,
    parse_bundle,
)


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
                 include_csv=True, csv_name="candidate_results.csv"):
    """Build a zip in-memory and return a Path-like to it (BytesIO)."""
    headers = headers if headers is not None else HEADERS
    image_filenames = image_filenames or set()
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
            zf.writestr(f"media/{name}", b"image-bytes")
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
                       round1=10, round2=12),
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c2", candidate_order=2,
                       round1=20, round2=22),
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
    assert cands[0].round1 == 10
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


# ---- image filename safety -----------------------------------------------


def test_image_filename_with_path_separator_is_dropped(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="../../../etc/passwd",
                       page1="subdir/legit.jpg"),
    ]
    path = _bundle_path(tmp_path, rows)
    parsed = parse_bundle(path)
    sub = parsed.rows[0]
    assert sub.images["clerk_signature"] is None
    assert sub.images["forms_picture_1st_page"] is None
    # ...and the unsafe names don't show up in missing_images either.
    assert "../../../etc/passwd" not in parsed.missing_images
    assert "subdir/legit.jpg" not in parsed.missing_images


def test_image_filename_with_backslash_is_dropped(tmp_path):
    rows = [
        _candidate_row(instance_id="uuid:s1", barcode="111",
                       candidate_id="c1", candidate_order=1,
                       round1=1, round2=1,
                       clerk_signature="..\\windows\\system32"),
    ]
    parsed = parse_bundle(_bundle_path(tmp_path, rows))
    assert parsed.rows[0].images["clerk_signature"] is None


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
