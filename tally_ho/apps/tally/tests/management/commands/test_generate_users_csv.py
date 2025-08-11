import csv
import os
import tempfile

from django.core.management import call_command
from django.test import TestCase


class TestGenerateUsersCSV(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up temporary files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_generate_with_default_values(self):
        """
        Test generating CSV with default values (1 user per role, tally_id=1)
        """
        output_file = os.path.join(self.temp_dir, "test_default.csv")

        call_command("generate_users_csv", output=output_file)

        # Verify file exists
        self.assertTrue(os.path.exists(output_file))

        # Read and verify CSV content
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have 7 users (1 per role)
            self.assertEqual(len(rows), 7)

            # Verify headers
            self.assertEqual(
                reader.fieldnames,
                ["name", "username", "role", "admin", "tally_id"],
            )

            # Check first user (Audit Clerk)
            self.assertEqual(rows[0]["name"], "Audit Clerk 01")
            self.assertEqual(rows[0]["username"], "aud-01")
            self.assertEqual(rows[0]["role"], "Audit Clerk")
            self.assertEqual(rows[0]["admin"], "No")
            self.assertEqual(rows[0]["tally_id"], "1")

            # Check last user (Correction Clerk)
            self.assertEqual(rows[6]["name"], "Correction Clerk 01")
            self.assertEqual(rows[6]["username"], "cor-01")
            self.assertEqual(rows[6]["role"], "Correction Clerk")

    def test_generate_with_custom_values(self):
        """Test generating CSV with custom counts and tally_id"""
        output_file = os.path.join(self.temp_dir, "test_custom.csv")

        call_command(
            "generate_users_csv",
            audit_count=3,
            intake_count=2,
            clearance_count=0,  # Test zero count
            quality_control_count=1,
            data_entry_1_count=4,
            data_entry_2_count=4,
            corrections_count=2,
            tally_id=5,
            output=output_file,
        )

        # Read and verify CSV content
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have 16 users (3+2+0+1+4+4+2)
            self.assertEqual(len(rows), 16)

            # Verify tally_id
            for row in rows:
                self.assertEqual(row["tally_id"], "5")

            # Check username patterns
            audit_users = [row for row in rows if row["role"] == "Audit Clerk"]
            self.assertEqual(len(audit_users), 3)
            self.assertEqual(audit_users[0]["username"], "aud-01")
            self.assertEqual(audit_users[1]["username"], "aud-02")
            self.assertEqual(audit_users[2]["username"], "aud-03")

            # Verify no Clearance Clerk users (count was 0)
            clearance_users = [
                row for row in rows if row["role"] == "Clearance Clerk"
            ]
            self.assertEqual(len(clearance_users), 0)

    def test_username_formatting(self):
        """Test that usernames are properly formatted with leading zeros"""
        output_file = os.path.join(self.temp_dir, "test_formatting.csv")

        call_command(
            "generate_users_csv",
            audit_count=12,  # Test double-digit formatting
            output=output_file,
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            audit_users = [row for row in rows if row["role"] == "Audit Clerk"]

            # Check formatting with leading zeros
            self.assertEqual(audit_users[0]["username"], "aud-01")
            self.assertEqual(audit_users[8]["username"], "aud-09")
            self.assertEqual(audit_users[9]["username"], "aud-10")
            self.assertEqual(audit_users[11]["username"], "aud-12")

            # Check name formatting
            self.assertEqual(audit_users[0]["name"], "Audit Clerk 01")
            self.assertEqual(audit_users[9]["name"], "Audit Clerk 10")

    def test_all_role_types(self):
        """Test that all role types are correctly generated"""
        output_file = os.path.join(self.temp_dir, "test_all_roles.csv")

        call_command(
            "generate_users_csv",
            audit_count=1,
            intake_count=1,
            clearance_count=1,
            quality_control_count=1,
            data_entry_1_count=1,
            data_entry_2_count=1,
            corrections_count=1,
            output=output_file,
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Verify each role type
            expected_roles = [
                ("Audit Clerk", "aud-01"),
                ("Intake Clerk", "intk-01"),
                ("Clearance Clerk", "clr-01"),
                ("Quality Control Clerk", "qar-01"),
                ("Data Entry 1 Clerk", "de1-01"),
                ("Data Entry 2 Clerk", "de2-01"),
                ("Correction Clerk", "cor-01"),
            ]

            for i, (role, username) in enumerate(expected_roles):
                self.assertEqual(rows[i]["role"], role)
                self.assertEqual(rows[i]["username"], username)

    def test_large_counts(self):
        """Test generating large numbers of users"""
        output_file = os.path.join(self.temp_dir, "test_large.csv")

        call_command(
            "generate_users_csv",
            audit_count=8,
            intake_count=12,
            clearance_count=5,
            quality_control_count=10,
            data_entry_1_count=30,
            data_entry_2_count=30,
            corrections_count=9,
            tally_id=2,
            output=output_file,
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have 104 users total
            self.assertEqual(len(rows), 104)

            # Verify counts per role
            role_counts = {}
            for row in rows:
                role = row["role"]
                role_counts[role] = role_counts.get(role, 0) + 1

            self.assertEqual(role_counts["Audit Clerk"], 8)
            self.assertEqual(role_counts["Intake Clerk"], 12)
            self.assertEqual(role_counts["Clearance Clerk"], 5)
            self.assertEqual(role_counts["Quality Control Clerk"], 10)
            self.assertEqual(role_counts["Data Entry 1 Clerk"], 30)
            self.assertEqual(role_counts["Data Entry 2 Clerk"], 30)
            self.assertEqual(role_counts["Correction Clerk"], 9)

            # Check last Data Entry 2 user has correct username
            de2_users = [
                row for row in rows if row["role"] == "Data Entry 2 Clerk"
            ]
            self.assertEqual(de2_users[-1]["username"], "de2-30")
            self.assertEqual(de2_users[-1]["name"], "Data Entry 2 Clerk 30")

    def test_output_file_path(self):
        """Test that custom output file paths work correctly"""
        custom_filename = "custom_users.csv"
        output_file = os.path.join(self.temp_dir, custom_filename)

        call_command("generate_users_csv", output=output_file)

        # Verify file exists at the specified path
        self.assertTrue(os.path.exists(output_file))
        self.assertEqual(os.path.basename(output_file), custom_filename)
