from django.contrib.auth.models import User, Group

from django.test import TestCase
from django.test import RequestFactory

from libya_tally.libs.permissions.groups import create_permission_groups, \
    add_user_to_group


class TestBase(TestCase):
    @classmethod
    def _create_user(cls, username='bob', password='bob'):
        return User.objects.create(username=username, password=password)

    def _create_and_login_user(self, username='bob', password='bob'):
        self.user = self._create_user(username, password)
        # to simulate login, assing user to a request object
        request = RequestFactory().get('/')
        request.user = self.user
        self.request = request

    def _create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, 13)

    def _add_user_to_group(self, user, name):
        count = user.groups.count()
        add_user_to_group(user, name)
        self.assertTrue(user.groups.count() > count)
