from django.contrib.auth.models import Group, User
from django.test import TestCase

from tally_system.libs.permissions.groups import create_permission_groups, \
    create_demo_users_with_groups


class TestGroups(TestCase):
    number_of_groups = 14

    def setUp(self):
        pass

    def test_create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, self.number_of_groups)

    def test_create_demo_users_with_groups(self):
        count = Group.objects.count()
        user_count = User.objects.count()
        password = '1234'
        create_demo_users_with_groups(password)
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, self.number_of_groups)
        user_diff_count = User.objects.count() - user_count
        self.assertEqual(user_diff_count, self.number_of_groups)
        user = User.objects.get(username='administrator')
        self.assertTrue(user.check_password(password))
