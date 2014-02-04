from django.core.exceptions import ImproperlyConfigured
from django.views.generic.base import View

from libya_tally.libs.permissions import groups
from libya_tally.libs.views.mixins import GroupRequiredMixin
from libya_tally.libs.tests.test_base import TestBase


class ViewGroupRequiredNoGroups(GroupRequiredMixin, View):
    pass


class ViewGroupRequired(GroupRequiredMixin, View):
    group_required = groups.INTAKE_CLERK


class TestGroupRequired(TestBase):
    def test_improperly_configured(self):
        view = ViewGroupRequiredNoGroups.as_view()
        self._create_and_login_user()
        with self.assertRaises(ImproperlyConfigured):
            view(self.request)

    def test_super_admin(self):
        view = ViewGroupRequired.as_view()
        self._create_and_login_user()

        self.assertFalse(view.check_membership(groups.ARCHIVE_CLERK))
        self.assertTrue(view.check_membership(groups.INTAKE_CLERK))
        self.assertTrue(view.check_membership(groups.SUPER_ADMINISTRATOR))
