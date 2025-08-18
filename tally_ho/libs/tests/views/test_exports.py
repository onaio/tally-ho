import csv
import os


from tally_ho.libs.tests.test_base import (
    create_ballot,
    create_candidate,
    create_center,
    create_electrol_race,
    create_reconciliation_form,
    create_result_form,
    create_station,
    create_sub_constituency,
    create_tally,
    TestBase,
)
from tally_ho.libs.views.exports import save_barcode_results


class TestExports(TestBase):
    def setUp(self):
        super().setUp()
        self._create_and_login_user()
        self.tally = create_tally()
        self.electrol_race = create_electrol_race(
            self.tally,
            election_level=0,
            ballot_name="Test Election"
        )
        self.ballot = create_ballot(self.tally, self.electrol_race)
        self.sub_con = create_sub_constituency(code=12345, tally=self.tally)
        self.center = create_center(
            tally=self.tally, sub_constituency=self.sub_con
        )
        self.station = create_station(self.center)

    def test_save_barcode_results_with_reconciliation(self):
        """Test that save_barcode_results exports reconciliation data including
        'total number of ballot papers in the box' field correctly."""

        # Create result form
        result_form = create_result_form(
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            tally=self.tally
        )

        # Create reconciliation form with the field that was causing the error
        create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_sorted_and_counted=42,  # This should appear in CSV
            number_of_voters=100,
            number_valid_votes=95,
            number_invalid_votes=5,
            number_of_voter_cards_in_the_ballot_box=98
        )

        # Create candidates for the ballot
        create_candidate(
            ballot=self.ballot,
            candidate_name="Test Candidate 1",
            tally=self.tally
        )
        create_candidate(
            ballot=self.ballot,
            candidate_name="Test Candidate 2",
            tally=self.tally
        )

        # Call the export function that was failing
        csv_filename = save_barcode_results(
            complete_barcodes=[result_form.barcode],
            output_duplicates=False,
            output_to_file=False,
            tally_id=self.tally.id
        )

        # Read and verify the CSV content
        with open(csv_filename, 'r') as f:
            csv_reader = csv.DictReader(f)
            headers = csv_reader.fieldnames

            # Verify the problematic field is in headers
            self.assertIn('total number of ballot papers in the box', headers)

            # Verify all expected reconciliation fields are present
            expected_recon_fields = [
                'invalid ballots',
                'number of voter cards in the ballot box',
                'received ballots papers',
                'valid votes',
                'total number of ballot papers in the box'
            ]
            for field in expected_recon_fields:
                self.assertIn(field, headers)

            # Read the actual data rows
            rows = list(csv_reader)

            # Should have rows for each candidate
            self.assertEqual(len(rows), 2)

            # Check that reconciliation data is present in rows
            for row in rows:
                self.assertEqual(row['invalid ballots'], '5')
                self.assertEqual(
                    row['number of voter cards in the ballot box'], '98'
                )
                self.assertEqual(row['received ballots papers'], '100')
                self.assertEqual(row['valid votes'], '95')
                # This is the field that was causing the error
                self.assertEqual(
                    row['total number of ballot papers in the box'], '42'
                )

        # Clean up the temporary file
        os.unlink(csv_filename)
