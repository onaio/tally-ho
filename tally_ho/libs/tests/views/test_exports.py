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
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.views.exports import (
    export_candidate_votes,
    save_barcode_results,
)


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

    def test_export_candidate_votes_basic(self):
        """Test basic export_candidate_votes functionality."""
        # Create candidates for the ballot
        candidate1 = create_candidate(
            ballot=self.ballot,
            candidate_name="Test Candidate 1",
            tally=self.tally
        )
        candidate2 = create_candidate(
            ballot=self.ballot,
            candidate_name="Test Candidate 2",
            tally=self.tally
        )

        # Create result form
        result_form = create_result_form(
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            tally=self.tally,
            form_state=FormState.ARCHIVED
        )

        # Call export function
        csv_filename = export_candidate_votes(
            save_barcodes=False,
            output_duplicates=False,
            output_to_file=False,
            show_disabled_candidates=True,
            tally_id=self.tally.id
        )

        # Verify CSV was created
        self.assertTrue(os.path.exists(csv_filename))

        # Read and verify the CSV content
        with open(csv_filename, 'r') as f:
            csv_reader = csv.DictReader(f)
            headers = csv_reader.fieldnames

            # Verify expected headers
            self.assertIn('ballot number', headers)
            self.assertIn('stations', headers)
            self.assertIn('stations completed', headers)
            self.assertIn('candidate 1 name', headers)
            self.assertIn('candidate 1 votes', headers)

            # Read the data rows
            rows = list(csv_reader)
            self.assertEqual(len(rows), 1)  # One ballot

            # Verify ballot data
            row = rows[0]
            self.assertEqual(row['ballot number'], str(self.ballot.number))

        # Clean up
        os.unlink(csv_filename)

    def test_export_candidate_votes_multiple_ballots(self):
        """Test export with multiple ballots."""
        # Create second ballot
        ballot2 = create_ballot(
            self.tally,
            self.electrol_race,
            number=2
        )

        # Create candidates for both ballots
        create_candidate(
            ballot=self.ballot,
            candidate_name="Ballot1 Candidate1",
            tally=self.tally
        )
        create_candidate(
            ballot=ballot2,
            candidate_name="Ballot2 Candidate1",
            tally=self.tally
        )

        # Create result forms for both ballots
        create_result_form(
            barcode="222222",
            serial_number=2,
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            tally=self.tally,
            form_state=FormState.ARCHIVED,            
        )
        create_result_form(
            ballot=ballot2,
            barcode="333333",
            serial_number=3,
            center=self.center,
            station_number=self.station.station_number + 1,
            tally=self.tally,
            form_state=FormState.ARCHIVED
        )

        # Call export function
        csv_filename = export_candidate_votes(
            save_barcodes=False,
            output_duplicates=False,
            output_to_file=False,
            show_disabled_candidates=True,
            tally_id=self.tally.id
        )

        # Verify CSV was created
        self.assertTrue(os.path.exists(csv_filename))

        # Read and verify the CSV content
        with open(csv_filename, 'r') as f:
            csv_reader = csv.DictReader(f)
            rows = list(csv_reader)

            # Should have rows for both ballots
            self.assertEqual(len(rows), 2)

            # Verify ballot numbers
            ballot_numbers = {row['ballot number'] for row in rows}
            self.assertEqual(
                ballot_numbers,
                {str(self.ballot.number), str(ballot2.number)}
            )

        # Clean up
        os.unlink(csv_filename)

    def test_export_candidate_votes_filter_disabled(self):
        """Test that disabled candidates are filtered when requested."""
        # Create active and disabled candidates
        active_candidate = create_candidate(
            ballot=self.ballot,
            candidate_name="Active Candidate",
            tally=self.tally,
            active=True
        )
        disabled_candidate = create_candidate(
            ballot=self.ballot,
            candidate_name="Disabled Candidate",
            tally=self.tally,
            active=False
        )

        # Create result form
        create_result_form(
            ballot=self.ballot,
            center=self.center,
            station_number=self.station.station_number,
            tally=self.tally,
            form_state=FormState.ARCHIVED
        )

        # Export with disabled candidates filtered out
        csv_filename = export_candidate_votes(
            save_barcodes=False,
            output_duplicates=False,
            output_to_file=False,
            show_disabled_candidates=False,
            tally_id=self.tally.id
        )

        # Verify CSV was created
        self.assertTrue(os.path.exists(csv_filename))

        # Read and verify the CSV content
        with open(csv_filename, 'r') as f:
            csv_reader = csv.DictReader(f)
            headers = csv_reader.fieldnames

            # Should only have columns for 1 candidate (the active one)
            self.assertIn('candidate 1 name', headers)
            self.assertNotIn('candidate 2 name', headers)

        # Clean up
        os.unlink(csv_filename)
