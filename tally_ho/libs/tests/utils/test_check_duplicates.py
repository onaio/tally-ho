import os

from django.test import TestCase
from tally_ho.apps.tally.management.commands.utils import (
    check_duplicates, DuplicateFoundError
)

class CheckDuplicatesTestCase(TestCase):
    def setUp(self):
        """Set up temporary CSV files for testing."""
        # CSV file with duplicates
        self.csv_with_duplicates = 'test_with_duplicates.csv'
        with open(self.csv_with_duplicates, 'w') as f:
            f.write("barcode,name\n")
            f.write("12345,Item A\n")
            f.write("67890,Item B\n")
            f.write("12345,Item A\n")  # Duplicate barcode

        # CSV file without duplicates
        self.csv_without_duplicates = 'test_without_duplicates.csv'
        with open(self.csv_without_duplicates, 'w') as f:
            f.write("barcode,name\n")
            f.write("12345,Item A\n")
            f.write("67890,Item B\n")
            f.write("54321,Item C\n")

    def tearDown(self):
        """Clean up the temporary CSV files."""
        os.remove(self.csv_with_duplicates)
        os.remove(self.csv_without_duplicates)

    def test_duplicates_exist(self):
        """Test that duplicates are correctly identified."""
        with self.assertRaises(DuplicateFoundError):
            check_duplicates(
                csv_file_path=self.csv_with_duplicates, field='barcode')

    def test_no_duplicates(self):
        """Test that no duplicates are correctly identified."""
        try:
            check_duplicates(
                csv_file_path=self.csv_without_duplicates, field='barcode')
        except DuplicateFoundError:
            self.fail(
                "check_duplicates() raised DuplicatesFoundError unexpectedly!")
