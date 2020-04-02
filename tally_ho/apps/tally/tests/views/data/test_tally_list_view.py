from django.test import RequestFactory

from tally_ho.apps.tally.views.data import tally_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally, TestBase


class TestTallyListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_tally_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.TallyListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Tally List")
        self.assertContains(response, "Id")
        self.assertContains(response, "Name")
        self.assertContains(response, "Creation")
        self.assertContains(response, "Last Modification")
        self.assertContains(response, "Administration")
        self.assertContains(response, "Actions")
