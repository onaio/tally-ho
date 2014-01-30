from django.core.exceptions import ImproperlyConfigured
from django.views.generic.base import View

from libya_tally.libs.tests.test_base import TestBase
from libya_tally.libs.views.mixins import GroupRequiredMixin


class ViewGroupRequired(GroupRequiredMixin, View):
    pass


class TestGroupRequired(TestBase):
    def test_improperly_configured(self):
        view = ViewGroupRequired.as_view()
        self._create_and_login_user()
        with self.assertRaises(ImproperlyConfigured):
            view(self.request)
