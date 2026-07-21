"""Emit a PVP upload bundle that matches a demo tally.

Produces a zip in the shape ``tally_ho.libs.pvp.bundle.parse_bundle`` expects:
``candidate_results.csv`` at the root plus stub ``media/*.jpg`` images. One
ODK submission per result form; one CSV row per (submission, candidate).
"""
import csv
import io
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.pvp.bundle import (
    CSV_NAME,
    IMAGE_COLUMNS,
    MEDIA_DIR,
    RECON_COLUMNS,
    REQUIRED_COLUMNS,
)


# REQUIRED_COLUMNS is a superset — RECON_COLUMNS is already splatted in
# and IMAGE_COLUMNS members are listed explicitly.
CSV_HEADERS = REQUIRED_COLUMNS
STUB_IMAGES = ("demo_sig.jpg", "demo_p1.jpg", "demo_p2.jpg")


def _stub_jpeg():
    """A genuine (tiny) JPEG. The import verifies every image with Pillow
    before storing it, so the stub must decode as a real image."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (204, 204, 204)).save(buffer, format="JPEG")
    return buffer.getvalue()


_STUB_JPEG = _stub_jpeg()
RECON_VALUES = {
    "reconciliation_r1-number_ballots_received_r1": 200,
    "reconciliation_r1-number_voter_cards_r1": 180,
    "reconciliation_r1-number_valid_ballots_r1": 175,
    "reconciliation_r1-number_invalid_ballots_r1": 5,
    "reconciliation_r1-number_ballots_inside_box_r1": 180,
    "reconciliation_r2-number_ballots_received_r2": 200,
    "reconciliation_r2-number_voter_cards_r2": 180,
    "reconciliation_r2-number_valid_ballots_r2": 175,
    "reconciliation_r2-number_invalid_ballots_r2": 5,
    "reconciliation_r2-number_ballots_inside_box_r2": 180,
}


def create_demo_pvp_bundle(tally, output):
    """Write a PVP bundle zip targeting every UNSUBMITTED form in ``tally``.

    :param tally: the ``Tally`` instance whose forms become submissions.
    :param output: filesystem path (str or ``Path``) of the zip to write.
    :returns: ``Path`` to the written zip.
    """
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = list(_build_rows(tally))
    if not rows:
        raise CommandError(
            f"tally {tally.id!r} has no result forms to bundle",
        )

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        zf.writestr(CSV_NAME, buffer.getvalue())
        for image_name in STUB_IMAGES:
            zf.writestr(f"{MEDIA_DIR}/{image_name}", _STUB_JPEG)

    return output_path


def _build_rows(tally):
    forms = (
        ResultForm.objects.filter(tally=tally)
        .select_related("ballot")
        .order_by("barcode")
    )
    for index, form in enumerate(forms, start=1):
        instance_id = f"uuid:demo-{tally.id}-{index}"
        candidates = form.ballot.candidates.order_by("order")
        for candidate in candidates:
            # PVP's whole premise is double-entry: the device only
            # emits when round1 == round2. The bundle parser enforces
            # this at parse time, so the demo bundle must mirror it.
            votes = _round2_votes(candidate.order, form.barcode)
            row = {
                "meta-instanceID": instance_id,
                "barcode": form.barcode,
                "ballot_number": str(form.ballot.number),
                "candidate_id": str(candidate.candidate_id),
                "candidate_order": str(candidate.order),
                "candidate_result_round1": str(votes),
                "candidate_result_round2": str(votes),
                "xml_form_id": f"results_demo_{tally.id}",
                "staff_user_name": "demo_clerk",
                "clerk_signature": STUB_IMAGES[0],
                "forms_picture_1st_page": STUB_IMAGES[1],
                "forms_picture_2nd_page": STUB_IMAGES[2],
            }
            for column in RECON_COLUMNS:
                row[column] = str(RECON_VALUES[column])
            for column in IMAGE_COLUMNS:
                row.setdefault(column, "")
            yield row


def _round2_votes(order, barcode):
    # Stub votes that vary by both candidate order *and* barcode so the
    # generated bundle doesn't trip the duplicate-result-tracking check
    # (which flags forms with identical vote patterns across all
    # candidates in the same ballot).
    base = max(0, 60 - 20 * (order - 1))
    jitter = int(barcode[-2:]) % 11
    return base + jitter


def _default_output(tally_id):
    # settings.BASE_DIR points at tally_ho/; the project's data/ lives one
    # level up alongside manage.py.
    project_root = Path(settings.BASE_DIR).parent
    return project_root / "data" / f"demo_pvp_bundle_{tally_id}.zip"


class Command(BaseCommand):
    help = (
        "Emit a PVP upload bundle zip targeting every result form in a "
        "demo tally."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tally-id",
            type=int,
            required=True,
            help="Tally ID whose result forms become bundle submissions.",
        )
        parser.add_argument(
            "--output",
            default=None,
            help=(
                "Path to write the zip (default: "
                "<BASE_DIR>/data/demo_pvp_bundle_<tally_id>.zip)."
            ),
        )

    def handle(self, *args, **options):
        tally_id = options["tally_id"]
        try:
            tally = Tally.objects.get(id=tally_id)
        except Tally.DoesNotExist as exc:
            raise CommandError(
                f"Tally with id {tally_id} does not exist",
            ) from exc

        output = options["output"] or _default_output(tally.id)
        written = create_demo_pvp_bundle(tally=tally, output=output)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo PVP bundle written: {written}",
            )
        )
