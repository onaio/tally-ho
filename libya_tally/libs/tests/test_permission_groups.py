from django.contrib.auth.models import Group, User
from django.test import TestCase

from libya_tally.libs.permissions.groups import create_permission_groups, \
    create_demo_users_with_groups


class TestPermissionsGroup(TestCase):
    def setUp(self):
        pass

    def test_create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, 13)

    def test_create_demo_users_with_groups(self):
        count = Group.objects.count()
        user_count = User.objects.count()
        password = '1234'
        create_demo_users_with_groups(password)
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, 13)
        user_diff_count = User.objects.count() - user_count
        self.assertEqual(user_diff_count, 13)
        user = User.objects.get(username='administrator')
        self.assertTrue(user.check_password(password))
