from django.contrib.auth.models import Group, User
from django.test import TestCase

from tally_ho.libs.permissions.groups import (
    create_permission_groups, add_user_to_group, user_groups,
    is_audit_clerk, is_audit_supervisor, is_tally_manager,
    is_super_administrator, AUDIT_CLERK, AUDIT_SUPERVISOR,
    TALLY_MANAGER, SUPER_ADMINISTRATOR
)


class TestGroups(TestCase):
    number_of_groups = 13

    def setUp(self):
        create_permission_groups()
        self.user =\
            User.objects.create_user('john', 'john@example.com', 'password')

    def test_create_permission_groups(self):
        count = Group.objects.count()
        self.assertEqual(count, self.number_of_groups)

    def test_add_user_to_group(self):
        # Test adding user to a group
        add_user_to_group(self.user, AUDIT_CLERK)
        self.assertTrue(self.user.groups.filter(name=AUDIT_CLERK).exists())

        # Test adding user to multiple groups
        add_user_to_group(self.user, AUDIT_SUPERVISOR)
        self.assertEqual(self.user.groups.count(), 2)

    def test_user_groups(self):
        # Test with no groups
        self.assertEqual(list(user_groups(self.user)), [])

        # Test with one group
        add_user_to_group(self.user, AUDIT_CLERK)
        self.assertEqual(list(user_groups(self.user)), [AUDIT_CLERK])

        # Test with multiple groups
        add_user_to_group(self.user, AUDIT_SUPERVISOR)
        groups = list(user_groups(self.user))
        self.assertEqual(len(groups), 2)
        self.assertIn(AUDIT_CLERK, groups)
        self.assertIn(AUDIT_SUPERVISOR, groups)

        # Test with anonymous user
        self.assertEqual(list(user_groups(None)), [])

    def test_group_membership_checks(self):
        # Test is_audit_clerk
        self.assertFalse(is_audit_clerk(self.user))
        add_user_to_group(self.user, AUDIT_CLERK)
        self.assertTrue(is_audit_clerk(self.user))

        # Test is_audit_supervisor
        self.assertFalse(is_audit_supervisor(self.user))
        add_user_to_group(self.user, AUDIT_SUPERVISOR)
        self.assertTrue(is_audit_supervisor(self.user))

        # Test is_tally_manager
        self.assertFalse(is_tally_manager(self.user))
        add_user_to_group(self.user, TALLY_MANAGER)
        self.assertTrue(is_tally_manager(self.user))

        # Test is_super_administrator
        self.assertFalse(is_super_administrator(self.user))
        add_user_to_group(self.user, SUPER_ADMINISTRATOR)
        self.assertTrue(is_super_administrator(self.user))
