from django.test import RequestFactory

from tally_ho.apps.tally.views.data import center_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally, TestBase


class TestCenterListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_center_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CenterListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Center and Station List")
        self.assertContains(response, "Download")
        self.assertContains(response, "New Station")
        self.assertContains(response, "New Center")
