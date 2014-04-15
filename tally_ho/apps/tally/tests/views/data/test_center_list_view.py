from django.test import RequestFactory

from tally_ho.apps.tally.views.data import center_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import TestBase


class TestSuperAdmin(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_center_list_view(self):
        view = views.CenterListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Center and Station List")
