from django.contrib.auth.models import Group
from django.test import TestCase

from libya_tally.libs.permissions.groups import create_permission_groups


class TestPermissionsGroup(TestCase):
    def setUp(self):
        pass

    def test_create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, 13)
