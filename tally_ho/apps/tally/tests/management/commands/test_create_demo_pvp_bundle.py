import tempfile
from pathlib import Path

from django.test import TestCase

from tally_ho.apps.tally.management.commands.create_demo_pvp_bundle import (
    create_demo_pvp_bundle,
)
from tally_ho.apps.tally.management.commands.create_demo_tally import (
    create_demo_tally,
)
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.pvp.bundle import parse_bundle


class TestCreateDemoPvpBundle(TestCase):
    def setUp(self):
        self.tally = create_demo_tally(name="Demo Tally")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "demo.zip"

    def test_writes_parseable_bundle_one_submission_per_form(self):
        create_demo_pvp_bundle(tally=self.tally, output=self.output)

        parsed = parse_bundle(self.output)
        form_count = ResultForm.objects.filter(tally=self.tally).count()
        self.assertEqual(parsed.total, form_count)
        self.assertEqual(parsed.missing_images, [])

    def test_each_submission_has_one_row_per_candidate(self):
        create_demo_pvp_bundle(tally=self.tally, output=self.output)

        parsed = parse_bundle(self.output)
        for submission in parsed.rows:
            form = ResultForm.objects.get(
                tally=self.tally, barcode=submission.barcode,
            )
            expected = Candidate.objects.filter(ballot=form.ballot).count()
            self.assertEqual(len(submission.candidates), expected)

    def test_barcodes_match_demo_tally(self):
        create_demo_pvp_bundle(tally=self.tally, output=self.output)

        parsed = parse_bundle(self.output)
        bundle_barcodes = sorted(s.barcode for s in parsed.rows)
        tally_barcodes = sorted(
            ResultForm.objects.filter(tally=self.tally).values_list(
                "barcode", flat=True,
            ),
        )
        self.assertEqual(bundle_barcodes, tally_barcodes)

    def test_round2_votes_populated(self):
        create_demo_pvp_bundle(tally=self.tally, output=self.output)

        parsed = parse_bundle(self.output)
        for submission in parsed.rows:
            for candidate in submission.candidates:
                self.assertIsNotNone(candidate.round2)
                self.assertGreaterEqual(candidate.round2, 0)

    def test_recon_r2_fields_populated(self):
        create_demo_pvp_bundle(tally=self.tally, output=self.output)

        parsed = parse_bundle(self.output)
        for submission in parsed.rows:
            for key in (
                "reconciliation_r2-number_voter_cards_r2",
                "reconciliation_r2-number_valid_ballots_r2",
                "reconciliation_r2-number_invalid_ballots_r2",
                "reconciliation_r2-number_ballots_inside_box_r2",
            ):
                self.assertIsNotNone(submission.recon[key])
