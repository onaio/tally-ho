from django.contrib.auth.models import Group, User
from django.test import TestCase

from tally_ho.apps.tally.management.commands.create_demo_users import (
    create_demo_users_with_groups,
)


class TestCreateDemoUsers(TestCase):
    number_of_groups = 13

    def test_create_demo_users_with_groups(self):
        count = Group.objects.count()
        user_count = User.objects.count()
        password = '1234'
        create_demo_users_with_groups(password=password)
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, self.number_of_groups)
        user_diff_count = User.objects.count() - user_count
        self.assertEqual(user_diff_count, self.number_of_groups)
        user = User.objects.get(username='super_administrator')
        self.assertTrue(user.check_password(password))
