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

            # Should have 13 users (7 clerks + 4 supervisors + 2 admin roles)
            self.assertEqual(len(rows), 13)

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

            # Check Corrections Clerk (7th user)
            self.assertEqual(rows[6]["name"], "Corrections Clerk 01")
            self.assertEqual(rows[6]["username"], "cor-01")
            self.assertEqual(rows[6]["role"], "Corrections Clerk")

            # Check last user (Tally Manager)
            self.assertEqual(rows[12]["name"], "Tally Manager 01")
            self.assertEqual(rows[12]["username"], "tally_mgr-01")
            self.assertEqual(rows[12]["role"], "Tally Manager")

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
            # Set supervisor and admin counts to 0 for predictable test
            audit_supervisor_count=0,
            intake_supervisor_count=0,
            clearance_supervisor_count=0,
            quality_control_supervisor_count=0,
            super_administrator_count=0,
            tally_manager_count=0,
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

            # Verify each role type (now 13 roles total)
            expected_roles = [
                ("Audit Clerk", "aud-01"),
                ("Intake Clerk", "intk-01"),
                ("Clearance Clerk", "clr-01"),
                ("Quality Control Clerk", "qar-01"),
                ("Data Entry 1 Clerk", "de1-01"),
                ("Data Entry 2 Clerk", "de2-01"),
                ("Corrections Clerk", "cor-01"),
                ("Audit Supervisor", "aud_sup-01"),
                ("Intake Supervisor", "intk_sup-01"),
                ("Clearance Supervisor", "clr_sup-01"),
                ("Quality Control Supervisor", "qar_sup-01"),
                ("Super Administrator", "super_admin-01"),
                ("Tally Manager", "tally_mgr-01"),
            ]

            self.assertEqual(len(rows), 13)  # All 13 roles
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
            # Set supervisor and admin counts to 0 for predictable test
            audit_supervisor_count=0,
            intake_supervisor_count=0,
            clearance_supervisor_count=0,
            quality_control_supervisor_count=0,
            super_administrator_count=0,
            tally_manager_count=0,
            tally_id=2,
            output=output_file,
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have 104 users total (clerks only in this test)
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
            self.assertEqual(role_counts["Corrections Clerk"], 9)

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

    def test_include_tally_in_username_flag(self):
        """Test the --include-tally-in-username flag functionality"""
        output_file = os.path.join(self.temp_dir, "test_tally_usernames.csv")

        # Generate with tally ID in usernames
        call_command(
            "generate_users_csv",
            audit_count=2,
            intake_count=1,
            clearance_count=0,
            quality_control_count=1,
            data_entry_1_count=2,
            data_entry_2_count=0,
            corrections_count=0,
            # Set supervisor and admin counts to 0 for predictable test
            audit_supervisor_count=0,
            intake_supervisor_count=0,
            clearance_supervisor_count=0,
            quality_control_supervisor_count=0,
            super_administrator_count=0,
            tally_manager_count=0,
            tally_id=5,
            include_tally_in_username=True,
            output=output_file,
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have 6 users (2+1+0+1+2+0+0)
            self.assertEqual(len(rows), 6)

            # Check that usernames include tally ID
            audit_users = [row for row in rows if row["role"] == "Audit Clerk"]
            self.assertEqual(len(audit_users), 2)
            self.assertEqual(audit_users[0]["username"], "aud-5-01")
            self.assertEqual(audit_users[1]["username"], "aud-5-02")

            intake_users = [
                row for row in rows if row["role"] == "Intake Clerk"
            ]
            self.assertEqual(len(intake_users), 1)
            self.assertEqual(intake_users[0]["username"], "intk-5-01")

            qar_users = [
                row for row in rows if row["role"] == "Quality Control Clerk"
            ]
            self.assertEqual(len(qar_users), 1)
            self.assertEqual(qar_users[0]["username"], "qar-5-01")

            de1_users = [
                row for row in rows if row["role"] == "Data Entry 1 Clerk"
            ]
            self.assertEqual(len(de1_users), 2)
            self.assertEqual(de1_users[0]["username"], "de1-5-01")
            self.assertEqual(de1_users[1]["username"], "de1-5-02")

    def test_username_without_tally_flag_default(self):
        """Test default behavior remains unchanged (no tally in username)"""
        output_file = os.path.join(self.temp_dir, "test_default_usernames.csv")

        # Generate WITHOUT the flag (default behavior)
        call_command(
            "generate_users_csv",
            audit_count=2,
            intake_count=1,
            tally_id=7,  # Even with high tally ID, shouldn't appear
            output=output_file,
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Check that usernames do NOT include tally ID (default behavior)
            audit_users = [row for row in rows if row["role"] == "Audit Clerk"]
            self.assertEqual(audit_users[0]["username"], "aud-01")
            self.assertEqual(audit_users[1]["username"], "aud-02")

            intake_users = [
                row for row in rows if row["role"] == "Intake Clerk"
            ]
            self.assertEqual(intake_users[0]["username"], "intk-01")

            # But tally_id should still be in the CSV field
            for row in rows:
                self.assertEqual(row["tally_id"], "7")

    def test_tally_in_username_with_different_tally_ids(self):
        """Test that different tally IDs work correctly in usernames"""
        test_cases = [
            {"tally_id": 1, "expected_prefix": "aud-1"},
            {"tally_id": 10, "expected_prefix": "aud-10"},
            {"tally_id": 999, "expected_prefix": "aud-999"},
        ]

        for i, case in enumerate(test_cases):
            output_file = os.path.join(
                self.temp_dir, f"test_tally_{case['tally_id']}.csv"
            )

            call_command(
                "generate_users_csv",
                audit_count=1,
                intake_count=0,
                clearance_count=0,
                quality_control_count=0,
                data_entry_1_count=0,
                data_entry_2_count=0,
                corrections_count=0,
                # Set supervisor and admin counts to 0 for predictable test
                audit_supervisor_count=0,
                intake_supervisor_count=0,
                clearance_supervisor_count=0,
                quality_control_supervisor_count=0,
                super_administrator_count=0,
                tally_manager_count=0,
                tally_id=case["tally_id"],
                include_tally_in_username=True,
                output=output_file,
            )

            with open(output_file, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                self.assertEqual(len(rows), 1)
                expected_username = f"{case['expected_prefix']}-01"
                self.assertEqual(rows[0]["username"], expected_username)
                self.assertEqual(rows[0]["tally_id"], str(case["tally_id"]))

    def test_supervisor_and_admin_roles(self):
        """Test generation of supervisor and admin roles"""
        output_file = os.path.join(self.temp_dir, "test_supervisors.csv")

        call_command(
            "generate_users_csv",
            # Set all clerk counts to 0
            audit_count=0,
            intake_count=0,
            clearance_count=0,
            quality_control_count=0,
            data_entry_1_count=0,
            data_entry_2_count=0,
            corrections_count=0,
            # Set supervisor and admin counts
            audit_supervisor_count=2,
            intake_supervisor_count=1,
            clearance_supervisor_count=1,
            quality_control_supervisor_count=2,
            super_administrator_count=1,
            tally_manager_count=2,
            tally_id=3,
            output=output_file,
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have 9 users (2+1+1+2+1+2)
            self.assertEqual(len(rows), 9)

            # Check Audit Supervisors
            audit_sups = [
                row for row in rows if row["role"] == "Audit Supervisor"
            ]
            self.assertEqual(len(audit_sups), 2)
            self.assertEqual(audit_sups[0]["username"], "aud_sup-01")
            self.assertEqual(audit_sups[1]["username"], "aud_sup-02")

            # Check Super Administrator
            super_admins = [
                row for row in rows if row["role"] == "Super Administrator"
            ]
            self.assertEqual(len(super_admins), 1)
            self.assertEqual(super_admins[0]["username"], "super_admin-01")
            # Super Administrator should have admin privileges
            self.assertEqual(super_admins[0]["admin"], "Yes")

            # Check Tally Managers
            tally_mgrs = [
                row for row in rows if row["role"] == "Tally Manager"
            ]
            self.assertEqual(len(tally_mgrs), 2)
            self.assertEqual(tally_mgrs[0]["username"], "tally_mgr-01")
            self.assertEqual(tally_mgrs[1]["username"], "tally_mgr-02")
            # Tally Manager should NOT have admin privileges
            self.assertEqual(tally_mgrs[0]["admin"], "No")

            # Verify all have correct tally_id
            for row in rows:
                self.assertEqual(row["tally_id"], "3")
                # Verify admin field is correct
                if row["role"] == "Super Administrator":
                    self.assertEqual(row["admin"], "Yes")
                else:
                    self.assertEqual(row["admin"], "No")
