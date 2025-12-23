from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.libs.tests.test_base import create_tally


class TestCreateQuarantineChecks(TestCase):
    def setUp(self):
        self.tally = create_tally()
        self.quarantine_data = getattr(settings, "QUARANTINE_DATA")

    def test_create_quarantine_checks_requires_tally_id(self):
        """Test that the command requires --tally-id argument."""
        with self.assertRaises(CommandError)  as context:
            call_command("create_quarantine_checks")
        self.assertIn("the following arguments are required: --tally-id", str(context.exception))

    def test_create_quarantine_checks_with_invalid_tally_id(self):
        """Test that the command fails with invalid tally_id."""
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command(
                "create_quarantine_checks", "--tally-id", 99999, stdout=out
            )
        self.assertIn("Tally with id 99999 does not exist", str(context.exception))

    def test_create_quarantine_checks_with_valid_tally_id(self):
        """Test that the command creates checks for valid tally_id."""
        out = StringIO()

        # Verify no checks exist initially
        initial_count = QuarantineCheck.objects.filter(
            tally_id=self.tally.pk
        ).count()
        self.assertEqual(initial_count, 0)

        # Run the command
        call_command(
            "create_quarantine_checks",
            "--tally-id",
            self.tally.pk,
            stdout=out,
        )

        # Verify checks were created
        final_count = QuarantineCheck.objects.filter(
            tally_id=self.tally.pk
        ).count()
        expected_count = len(self.quarantine_data)
        self.assertEqual(final_count, expected_count)

    def test_create_quarantine_checks_does_not_duplicate(self):
        """Test that running the command twice doesn't create duplicates."""
        out = StringIO()

        # Run the command first time
        call_command(
            "create_quarantine_checks",
            "--tally-id",
            self.tally.pk,
            stdout=out,
        )
        first_count = QuarantineCheck.objects.filter(
            tally_id=self.tally.pk
        ).count()

        # Run the command second time
        call_command(
            "create_quarantine_checks",
            "--tally-id",
            self.tally.pk,
            stdout=out,
        )
        second_count = QuarantineCheck.objects.filter(
            tally_id=self.tally.pk
        ).count()

        # Count should remain the same
        self.assertEqual(first_count, second_count)
        expected_count = len(self.quarantine_data)
        self.assertEqual(second_count, expected_count)

    def test_create_quarantine_checks_creates_correct_methods(self):
        """Test that all expected quarantine check methods are created."""
        call_command(
            "create_quarantine_checks",
            "--tally-id",
            self.tally.pk,
        )

        # Verify all expected methods exist
        for check_data in self.quarantine_data:
            exists = QuarantineCheck.objects.filter(
                tally_id=self.tally.pk, method=check_data["method"]
            ).exists()
            self.assertTrue(
                exists,
                f"QuarantineCheck with method {check_data['method']} "
                f"was not created",
            )

    def test_create_quarantine_checks_sets_tally_id(self):
        """Test that all created checks have the correct tally_id."""
        call_command(
            "create_quarantine_checks",
            "--tally-id",
            self.tally.pk,
        )

        # Verify all checks have correct tally_id
        checks = QuarantineCheck.objects.filter(tally_id=self.tally.pk)
        for check in checks:
            self.assertEqual(check.tally_id, self.tally.pk)
