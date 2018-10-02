from django.contrib.auth.models import Group
from django.test import TestCase

from tally_ho.libs.permissions.groups import create_permission_groups


class TestGroups(TestCase):
    number_of_groups = 13

    def setUp(self):
        pass

    def test_create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, self.number_of_groups)
