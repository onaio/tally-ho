from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups


class TestMigrateUsersTallyCommand(TestCase):
    def setUp(self):
        # Create test tallies
        self.source_tally = Tally.objects.create(name="Source Tally")
        self.target_tally = Tally.objects.create(name="Target Tally")
        self.admin_tally = Tally.objects.create(name="Admin Tally")

        # Create test groups
        self.audit_group = Group.objects.create(name=groups.AUDIT_CLERK)
        self.admin_group = Group.objects.create(
            name=groups.SUPER_ADMINISTRATOR
        )

        # Create test users
        self.user1 = UserProfile.objects.create(
            username="user1",
            first_name="User",
            last_name="One",
            tally=self.source_tally
        )
        self.user1.groups.add(self.audit_group)

        self.user2 = UserProfile.objects.create(
            username="user2",
            first_name="User",
            last_name="Two",
            tally=self.source_tally
        )
        self.user2.groups.add(self.admin_group)
        self.user2.administrated_tallies.add(self.admin_tally)

        self.user3 = UserProfile.objects.create(
            username="user3",
            first_name="User",
            last_name="Three",
            tally=self.source_tally
        )

        # User in different tally (should not be affected)
        self.other_user = UserProfile.objects.create(
            username="other_user",
            first_name="Other",
            last_name="User",
            tally=self.target_tally
        )

    def call_command_with_output(self, *args, **kwargs):
        """Helper to capture command output"""
        out = StringIO()
        call_command("migrate_users_tally", *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_migrate_all_users(self):
        """Test migrating all users from source to target tally"""
        output = self.call_command_with_output(
            source_tally=self.source_tally.id,
            target_tally=self.target_tally.id,
            all_users=True
        )

        # Check that all source tally users were migrated
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()
        self.other_user.refresh_from_db()

        self.assertEqual(self.user1.tally, self.target_tally)
        self.assertEqual(self.user2.tally, self.target_tally)
        self.assertEqual(self.user3.tally, self.target_tally)
        # Was already in target
        self.assertEqual(self.other_user.tally, self.target_tally)

        # Check that groups are preserved
        self.assertIn(self.audit_group, self.user1.groups.all())
        self.assertIn(self.admin_group, self.user2.groups.all())

        # Check that admin tallies are removed by default
        self.assertEqual(self.user2.administrated_tallies.count(), 0)

        self.assertIn("Migration completed successfully!", output)
        self.assertIn("Total users migrated: 3", output)

    def test_migrate_specific_users(self):
        """Test migrating specific users by username"""
        output = self.call_command_with_output(
            source_tally=self.source_tally.id,
            target_tally=self.target_tally.id,
            usernames="user1,user3"
        )

        # Check migration results
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()

        self.assertEqual(self.user1.tally, self.target_tally)
        self.assertEqual(self.user2.tally, self.source_tally)  # Not migrated
        self.assertEqual(self.user3.tally, self.target_tally)

        self.assertIn("Total users migrated: 2", output)

    def test_migrate_with_exclusions(self):
        """Test migrating all users except excluded ones"""
        output = self.call_command_with_output(
            source_tally=self.source_tally.id,
            target_tally=self.target_tally.id,
            all_users=True,
            exclude_usernames="user2"
        )

        # Check migration results
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()

        self.assertEqual(self.user1.tally, self.target_tally)
        self.assertEqual(self.user2.tally, self.source_tally)  # Excluded
        self.assertEqual(self.user3.tally, self.target_tally)

        self.assertIn("Total users migrated: 2", output)

    def test_preserve_admin_tallies(self):
        """Test preserving administrated tallies during migration"""
        self.call_command_with_output(
            source_tally=self.source_tally.id,
            target_tally=self.target_tally.id,
            usernames="user2",
            preserve_admin_tallies=True
        )

        # Check that admin tallies are preserved
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.tally, self.target_tally)
        self.assertEqual(self.user2.administrated_tallies.count(), 1)
        self.assertIn(self.admin_tally, self.user2.administrated_tallies.all())

    def test_dry_run(self):
        """Test dry run mode doesn't make changes"""
        output = self.call_command_with_output(
            source_tally=self.source_tally.id,
            target_tally=self.target_tally.id,
            all_users=True,
            dry_run=True
        )

        # Check that no changes were made
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        self.user3.refresh_from_db()

        self.assertEqual(self.user1.tally, self.source_tally)
        self.assertEqual(self.user2.tally, self.source_tally)
        self.assertEqual(self.user3.tally, self.source_tally)

        self.assertIn("DRY RUN: No changes were made", output)

    def test_invalid_source_tally(self):
        """Test error handling for invalid source tally"""
        with self.assertRaises(CommandError) as cm:
            call_command(
                "migrate_users_tally",
                source_tally=9999,
                target_tally=self.target_tally.id,
                all_users=True
            )
        self.assertIn(
            "Source tally with ID '9999' does not exist", str(cm.exception)
        )

    def test_invalid_target_tally(self):
        """Test error handling for invalid target tally"""
        with self.assertRaises(CommandError) as cm:
            call_command(
                "migrate_users_tally",
                source_tally=self.source_tally.id,
                target_tally=9999,
                all_users=True
            )
        self.assertIn(
            "Target tally with ID '9999' does not exist", str(cm.exception)
        )

    def test_same_source_and_target(self):
        """Test error when source and target tally are the same"""
        with self.assertRaises(CommandError) as cm:
            call_command(
                "migrate_users_tally",
                source_tally=self.source_tally.id,
                target_tally=self.source_tally.id,
                all_users=True
            )
        self.assertIn(
            "Source and target tally cannot be the same", str(cm.exception)
        )

    def test_missing_user_selection(self):
        """Test error when neither --all-users nor --usernames is specified"""
        with self.assertRaises(CommandError) as cm:
            call_command(
                "migrate_users_tally",
                source_tally=self.source_tally.id,
                target_tally=self.target_tally.id
            )
        self.assertIn(
            "Either --all-users or --usernames must be specified",
            str(cm.exception)
        )

    def test_conflicting_user_selection(self):
        """Test error when both --all-users and --usernames are specified"""
        with self.assertRaises(CommandError) as cm:
            call_command(
                "migrate_users_tally",
                source_tally=self.source_tally.id,
                target_tally=self.target_tally.id,
                all_users=True,
                usernames="user1"
            )
        self.assertIn(
            "Cannot specify both --all-users and --usernames",
            str(cm.exception)
        )

    def test_nonexistent_username(self):
        """Test error when specified username doesn't exist in source tally"""
        with self.assertRaises(CommandError) as cm:
            call_command(
                "migrate_users_tally",
                source_tally=self.source_tally.id,
                target_tally=self.target_tally.id,
                usernames="user1,nonexistent_user"
            )
        self.assertIn(
            "do not exist in source tally: nonexistent_user", str(cm.exception)
        )

    def test_no_users_to_migrate(self):
        """Test handling when no users match the criteria"""
        # Create a tally with no users
        empty_tally = Tally.objects.create(name="Empty Tally")

        output = self.call_command_with_output(
            source_tally=empty_tally.id,
            target_tally=self.target_tally.id,
            all_users=True
        )

        self.assertIn("No users found to migrate", output)

    def test_migration_output_formatting(self):
        """Test that output contains expected information"""
        output = self.call_command_with_output(
            source_tally=self.source_tally.id,
            target_tally=self.target_tally.id,
            usernames="user1",
            preserve_admin_tallies=True,
            dry_run=True
        )

        # Check that output contains key information
        self.assertIn("Migration Summary:", output)
        self.assertIn(f"Source Tally: {self.source_tally.name}", output)
        self.assertIn(f"Target Tally: {self.target_tally.name}", output)
        self.assertIn("Users to migrate: 1", output)
        self.assertIn("Preserve admin tallies: True", output)
        self.assertIn("Dry run: True", output)
        self.assertIn("Users to be migrated:", output)
        self.assertIn("user1 (User One)", output)

