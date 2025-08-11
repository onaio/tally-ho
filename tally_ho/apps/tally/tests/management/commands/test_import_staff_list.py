import csv
import os
import tempfile

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups


class TestImportStaffList(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Create test tally
        self.test_tally = Tally.objects.create(name="Test Tally", active=True)
        # Create permission groups
        for group_name in groups.GROUPS:
            Group.objects.get_or_create(name=group_name)

    def tearDown(self):
        # Clean up temporary files
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(self.temp_dir)

    def create_staff_csv(self, filename, data):
        """Create a CSV file with staff template format"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "w", newline="") as csvfile:
            fieldnames = ["name", "username", "role", "admin", "tally_id"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return filepath

    def create_user_csv(self, filename, data):
        """Create a CSV file with user template format"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "w", newline="") as csvfile:
            fieldnames = ["username", "name", "role"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return filepath

    def test_default_staff_template(self):
        """Test importing with default staff template"""
        data = [
            {
                "name": "John Doe",
                "username": "john_doe",
                "role": "Audit Clerk",
                "admin": "No",
                "tally_id": self.test_tally.id,
            }
        ]
        csv_file = self.create_staff_csv("staff_test.csv", data)

        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        # Verify user was created
        user = UserProfile.objects.get(username="john_doe")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.tally, self.test_tally)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.groups.filter(name=groups.AUDIT_CLERK).exists())

    def test_user_template_flag(self):
        """Test importing with --user-template flag"""
        data = [
            {
                "username": "jane_doe",
                "name": "Jane Doe",
                "role": "Data Entry 1 Clerk",
            }
        ]
        csv_file = self.create_user_csv("user_test.csv", data)

        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="user",
            password_suffix="@Test2024",
        )

        # Verify user was created
        user = UserProfile.objects.get(username="jane_doe")
        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.last_name, "Doe")
        self.assertIsNone(user.tally)  # No tally assigned in user template
        self.assertFalse(user.is_staff)
        self.assertTrue(
            user.groups.filter(name=groups.DATA_ENTRY_1_CLERK).exists()
        )

    def test_staff_template_with_admin_rights(self):
        """Test admin rights assignment with staff template"""
        data = [
            {
                "name": "Admin User",
                "username": "admin_user",
                "role": "Super Administrator",
                "admin": "Yes",
                "tally_id": "",
            }
        ]
        csv_file = self.create_staff_csv("admin_test.csv", data)

        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        user = UserProfile.objects.get(username="admin_user")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(
            user.groups.filter(name=groups.SUPER_ADMINISTRATOR).exists()
        )

    def test_multiple_users_import(self):
        """Test importing multiple users at once"""
        data = [
            {
                "name": "User One",
                "username": "user1",
                "role": "Intake Clerk",
                "admin": "No",
                "tally_id": self.test_tally.id,
            },
            {
                "name": "User Two",
                "username": "user2",
                "role": "Quality Control Clerk",
                "admin": "No",
                "tally_id": self.test_tally.id,
            },
        ]
        csv_file = self.create_staff_csv("multiple_users.csv", data)

        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        self.assertTrue(UserProfile.objects.filter(username="user1").exists())
        self.assertTrue(UserProfile.objects.filter(username="user2").exists())

        user1 = UserProfile.objects.get(username="user1")
        user2 = UserProfile.objects.get(username="user2")

        self.assertTrue(user1.groups.filter(name=groups.INTAKE_CLERK).exists())
        self.assertTrue(
            user2.groups.filter(name=groups.QUALITY_CONTROL_CLERK).exists()
        )

    def test_existing_user_not_modified(self):
        """Test that existing users are NOT modified by import"""
        # Create initial user with specific data
        initial_user = UserProfile.objects.create_user(
            username="existing_user",
            first_name="Original",
            last_name="Name",
        )
        initial_user.set_password("original_password")
        initial_user.tally = self.test_tally
        initial_user.is_staff = True
        initial_user.save()

        # Add user to a group
        audit_group = Group.objects.get(name=groups.AUDIT_CLERK)
        initial_user.groups.add(audit_group)

        # Try to "import" the same user with different data
        import_data = [
            {
                "name": "Different Name",
                "username": "existing_user",
                "role": "Clearance Clerk",
                "admin": "No",
                "tally_id": "",  # Different tally assignment
            }
        ]
        csv_file = self.create_staff_csv("existing_user.csv", import_data)
        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        # Verify user data was NOT changed
        user = UserProfile.objects.get(username="existing_user")
        self.assertEqual(
            user.first_name, "Original"
        )  # Should remain unchanged
        self.assertEqual(user.last_name, "Name")  # Should remain unchanged
        self.assertEqual(
            user.tally, self.test_tally
        )  # Should remain unchanged
        self.assertTrue(user.is_staff)  # Should remain unchanged

        # User should still be in original group, not the new one
        self.assertTrue(user.groups.filter(name=groups.AUDIT_CLERK).exists())
        self.assertFalse(
            user.groups.filter(name=groups.CLEARANCE_CLERK).exists()
        )

    def test_invalid_tally_id(self):
        """Test handling of invalid tally ID"""
        data = [
            {
                "name": "Test User",
                "username": "test_user",
                "role": "Audit Clerk",
                "admin": "No",
                "tally_id": "99999",  # Non-existent tally ID
            }
        ]
        csv_file = self.create_staff_csv("invalid_tally.csv", data)

        # Should not raise exception, but should report error
        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        # User should not be created due to invalid tally
        self.assertFalse(
            UserProfile.objects.filter(username="test_user").exists()
        )

    def test_unknown_role(self):
        """Test handling of unknown role"""
        data = [
            {
                "name": "Test User",
                "username": "test_user",
                "role": "Unknown Role",  # Not in STAFF_ROLE_DICT
                "admin": "No",
                "tally_id": "",
            }
        ]
        csv_file = self.create_staff_csv("unknown_role.csv", data)

        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        # User should be created but not assigned to any group
        user = UserProfile.objects.get(username="test_user")
        self.assertEqual(user.groups.count(), 0)

    def test_nonexistent_file(self):
        """Test error handling for non-existent file"""
        with self.assertRaises(CommandError):
            call_command(
                "import_staff_list",
                csv_file="nonexistent.csv",
                csv_template="staff",
                password_suffix="@Test2024",
            )

    def test_empty_csv_file(self):
        """Test handling of empty CSV file"""
        empty_file = os.path.join(self.temp_dir, "empty.csv")
        open(empty_file, "w").close()  # Create empty file

        # Should handle gracefully
        call_command(
            "import_staff_list",
            csv_file=empty_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

    def test_malformed_csv(self):
        """Test handling of malformed CSV"""
        malformed_file = os.path.join(self.temp_dir, "malformed.csv")
        with open(malformed_file, "w") as f:
            f.write("name,username,role,admin,tally_id\n")
            f.write("John,john_doe,Audit")  # Missing columns

        # Should handle gracefully and report errors
        call_command(
            "import_staff_list",
            csv_file=malformed_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

    def test_role_mapping_variations(self):
        """Test various role name mappings"""
        data = [
            {
                "name": "User One",
                "username": "user1",
                "role": "AUDIT CLERK",  # Uppercase
                "admin": "No",
                "tally_id": "",
            },
            {
                "name": "User Two",
                "username": "user2",
                "role": "correction",  # Lowercase, maps to CORRECTIONS_CLERK
                "admin": "No",
                "tally_id": "",
            },
        ]
        csv_file = self.create_staff_csv("role_variations.csv", data)

        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        user1 = UserProfile.objects.get(username="user1")
        user2 = UserProfile.objects.get(username="user2")

        self.assertTrue(user1.groups.filter(name=groups.AUDIT_CLERK).exists())
        self.assertTrue(
            user2.groups.filter(name=groups.CORRECTIONS_CLERK).exists()
        )

    def test_name_parsing(self):
        """Test name parsing into first_name and last_name"""
        data = [
            {
                "name": "John",  # Single name
                "username": "john",
                "role": "Audit Clerk",
                "admin": "No",
                "tally_id": "",
            },
            {
                "name": "Jane Mary Doe",  # Multiple names
                "username": "jane_doe",
                "role": "Audit Clerk",
                "admin": "No",
                "tally_id": "",
            },
        ]
        csv_file = self.create_staff_csv("name_parsing.csv", data)

        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        john = UserProfile.objects.get(username="john")
        jane = UserProfile.objects.get(username="jane_doe")

        self.assertEqual(john.first_name, "John")
        self.assertEqual(john.last_name, "")

        self.assertEqual(jane.first_name, "Jane")
        self.assertEqual(jane.last_name, "Mary Doe")

    def test_password_suffix_validation(self):
        """Test password suffix validation"""
        data = [
            {
                "name": "Test User",
                "username": "test_user",
                "role": "Audit Clerk",
                "admin": "No",
                "tally_id": "",
            }
        ]
        csv_file = self.create_staff_csv("suffix_test.csv", data)

        # Test missing password suffix
        with self.assertRaises(CommandError) as cm:
            call_command(
                "import_staff_list", csv_file=csv_file, csv_template="staff"
            )
        self.assertIn("required: --password-suffix", str(cm.exception))

        # Test short password suffix (less than 4 characters)
        with self.assertRaises(CommandError) as cm:
            call_command(
                "import_staff_list",
                csv_file=csv_file,
                csv_template="staff",
                password_suffix="123",
            )
        self.assertIn(
            "Password suffix must be at least 4 characters", str(cm.exception)
        )

        # Test valid password suffix - password should be username + suffix
        call_command(
            "import_staff_list",
            csv_file=csv_file,
            csv_template="staff",
            password_suffix="@Valid2024",
        )
        user = UserProfile.objects.get(username="test_user")
        # Password should be username + suffix
        has_suffix = user.check_password("test_user@Valid2024")
        has_username = user.check_password("test_user")
        self.assertTrue(
            has_suffix,
            f"Password with suffix failed. Username only: {has_username}, "
            f"reset_password: {user.reset_password}",
        )
        self.assertFalse(has_username)  # Should NOT be just username
        self.assertTrue(
            user.reset_password
        )  # Should be marked for password reset

    def test_integration_with_generate_users_csv(self):
        """Test importing CSV generated by generate_users_csv command"""
        # Generate CSV using the generate command
        output_file = os.path.join(self.temp_dir, "generated.csv")
        call_command(
            "generate_users_csv",
            audit_count=2,
            intake_count=1,
            clearance_count=0,
            tally_id=self.test_tally.id,
            output=output_file,
        )

        # Import the generated CSV
        call_command(
            "import_staff_list",
            csv_file=output_file,
            csv_template="staff",
            password_suffix="@Test2024",
        )

        # Verify users were created
        self.assertTrue(UserProfile.objects.filter(username="aud-01").exists())
        self.assertTrue(UserProfile.objects.filter(username="aud-02").exists())
        self.assertTrue(
            UserProfile.objects.filter(username="intk-01").exists()
        )

        # Verify tally assignment
        user = UserProfile.objects.get(username="aud-01")
        self.assertEqual(user.tally, self.test_tally)

    def test_update_fields_behavior(self):
        """Test that update_fields is respected in UserProfile.save()"""
        # Create a user with password suffix
        user = UserProfile.objects.create_user(
            username="test_update_fields",
            first_name="Test",
            last_name="User",
        )
        user.reset_password = True
        user.save(password_suffix="@Initial2024")

        # Verify initial password works
        self.assertTrue(user.check_password("test_update_fields@Initial2024"))

        # Now update only first_name using update_fields - password should NOT
        # change
        user.first_name = "Updated"
        user.save(update_fields=["first_name"])

        # Verify password is still the original one
        user.refresh_from_db()
        self.assertTrue(user.check_password("test_update_fields@Initial2024"))
        self.assertEqual(user.first_name, "Updated")
        self.assertTrue(user.reset_password)  # Should still be True

        # Now update including password field - password should change
        user.save(update_fields=["password"], password_suffix="@New2024")

        # Verify password changed
        user.refresh_from_db()
        self.assertTrue(user.check_password("test_update_fields@New2024"))
        self.assertFalse(user.check_password("test_update_fields@Initial2024"))

        # Test full save (no update_fields) - password should change again
        user.save(password_suffix="@Final2024")
        user.refresh_from_db()
        self.assertTrue(user.check_password("test_update_fields@Final2024"))
