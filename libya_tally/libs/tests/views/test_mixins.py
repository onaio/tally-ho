from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.views.generic.base import View

from libya_tally.libs.permissions import groups
from libya_tally.libs.views.mixins import GroupRequiredMixin
from libya_tally.libs.tests.test_base import TestBase


class ViewGroupRequiredNoGroups(GroupRequiredMixin, View):
    pass


class ViewGroupRequired(GroupRequiredMixin, View):
    group_required = groups.INTAKE_CLERK


class ViewTwoGroupsRequired(GroupRequiredMixin, View):
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]


class TestGroupRequired(TestBase):
    def test_improperly_configured(self):
        view = ViewGroupRequiredNoGroups.as_view()
        self._create_and_login_user()
        with self.assertRaises(ImproperlyConfigured):
            view(self.request)

    def test_super_admin(self):
        view = ViewGroupRequired.as_view()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

        try:
            view(self.request)
        except PermissionDenied:
            self.fail('view(self.request) raised PermissionDenied'
                      'unexpectedly')

    def test_multiple_groups_reject(self):
        view = ViewGroupRequired.as_view()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)

        try:
            view(self.request)
            self.fail('view(self.request) did not raise PermissionDenied')
        except PermissionDenied:
            pass

    def test_multiple_groups(self):
        view = ViewTwoGroupsRequired.as_view()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)

        try:
            view(self.request)
        except PermissionDenied:
            self.fail('view(self.request) raised PermissionDenied'
                      'unexpectedly')
