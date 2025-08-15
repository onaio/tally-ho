import io
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from reversion import revisions

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import (TestBase, create_result_form, 
                                          create_tally)


class TestShowResultFormHistory(TestBase):
    def setUp(self):
        self.tally1 = create_tally()
        self.tally2 = create_tally()
        
        # Create result form with some history
        with revisions.create_revision():
            self.result_form1 = create_result_form(
                form_state=FormState.INTAKE,
                tally=self.tally1,
                barcode='12345'
            )
            revisions.set_comment("Initial creation")
            
        # Create another result form with same barcode in different tally
        with revisions.create_revision():
            self.result_form2 = create_result_form(
                form_state=FormState.DATA_ENTRY_1,
                tally=self.tally2,
                barcode='12345'
            )
            revisions.set_comment("Second form creation")

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
        """Test command fails when multiple result forms exist without tally_id"""
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
            unique_form = create_result_form(
                form_state=FormState.INTAKE,
                tally=self.tally1,
                barcode='unique123'
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
        # Should contain CSV headers
        self.assertIn('Timestamp,User,Previous State,Current State', output)
        
    def test_command_with_no_version_history(self):
        """Test command with result form that has no version history"""
        # Create result form without revisions
        form_no_history = ResultForm.objects.create(
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