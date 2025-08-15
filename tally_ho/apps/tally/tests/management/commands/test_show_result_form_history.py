import io
import pathlib
import re

from django.core.management import call_command
from django.core.management.base import CommandError
from reversion import revisions

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import (TestBase, create_result_form,
                                           create_tally)


class TestShowResultFormHistory(TestBase):
    def setUp(self):
        self.tally1 = create_tally(name="TestTally1")
        self.tally2 = create_tally(name="TestTally2")

        # Create result form with some history
        with revisions.create_revision():
            self.result_form1 = create_result_form(
                form_state=FormState.INTAKE,
                tally=self.tally1,
                barcode='12345'
            )
            revisions.set_comment("Initial creation")

        # Create another result form with different barcode in different tally
        with revisions.create_revision():
            self.result_form2 = create_result_form(
                form_state=FormState.DATA_ENTRY_1,
                tally=self.tally2,
                barcode='67890',
                serial_number=1
            )
            revisions.set_comment("Second form creation")

        # Create a third result form with same barcode as first but in tally2
        # This should work because barcode+tally_id is the unique constraint
        with revisions.create_revision():
            self.result_form3 = create_result_form(
                form_state=FormState.QUALITY_CONTROL,
                tally=self.tally2,
                barcode='12345',
                serial_number=2
            )
            revisions.set_comment("Third form creation")

    def test_command_with_valid_barcode_and_tally_id(self):
        """Test command execution with valid barcode and tally_id"""
        out = io.StringIO()
        call_command(
            'show_result_form_history',
            '12345',
            tally_id=self.tally1.id,
            stdout=out
        )

        output = out.getvalue()
        self.assertIn('Result Form History: 12345', output)
        self.assertIn('INTAKE', output)

    def test_command_with_invalid_barcode(self):
        """Test command with non-existent barcode"""
        with self.assertRaises(CommandError) as cm:
            call_command('show_result_form_history', 'nonexistent')

        self.assertIn('does not exist', str(cm.exception))

    def test_command_with_multiple_tallies_no_tally_id(self):
        """Test command fails when multiple forms exist without tally_id"""
        with self.assertRaises(CommandError) as cm:
            call_command('show_result_form_history', '12345')

        error_message = str(cm.exception)
        self.assertIn('Multiple result forms found', error_message)
        self.assertIn('Please specify --tally-id', error_message)
        self.assertIn(f'Tally {self.tally1.id}', error_message)
        self.assertIn(f'Tally {self.tally2.id}', error_message)

    def test_command_with_unique_barcode_no_tally_id(self):
        """Test command works with unique barcode without tally_id"""
        # Create a result form with unique barcode
        with revisions.create_revision():
            create_result_form(
                form_state=FormState.INTAKE,
                tally=self.tally1,
                barcode='unique123',
                serial_number=3
            )

        out = io.StringIO()
        call_command('show_result_form_history', 'unique123', stdout=out)

        output = out.getvalue()
        self.assertIn('Result Form History: unique123', output)

    def test_command_csv_export(self):
        """Test CSV export functionality"""
        out = io.StringIO()
        call_command(
            'show_result_form_history',
            '12345',
            tally_id=self.tally1.id,
            export_csv=True,
            stdout=out
        )

        output = out.getvalue()
        # Should contain CSV export message
        self.assertIn('History exported to:', output)

        # Find the CSV filename in the output
        csv_match = re.search(r'History exported to: (\S+)', output)
        self.assertIsNotNone(csv_match)
        csv_filename = csv_match.group(1)

        # Check that CSV file exists and contains correct headers
        csv_path = pathlib.Path(csv_filename)
        self.assertTrue(csv_path.exists())

        with open(csv_path, 'r') as f:
            first_line = f.readline().strip()
            self.assertEqual(
                first_line,
                'barcode,user,timestamp,previous_state,current_state,duration_in_previous,is_current'
            )

        # Clean up
        csv_path.unlink()

    def test_command_with_no_version_history(self):
        """Test command with result form that has no version history"""
        # Create result form without revisions
        ResultForm.objects.create(
            barcode='nohistory',
            tally=self.tally1,
            form_state=FormState.UNSUBMITTED
        )

        out = io.StringIO()
        call_command(
            'show_result_form_history',
            'nohistory',
            tally_id=self.tally1.id,
            stdout=out
        )

        output = out.getvalue()
        self.assertIn('No version history found', output)
