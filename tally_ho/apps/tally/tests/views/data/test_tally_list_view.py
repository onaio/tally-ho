import json
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

    def test_tally_list_data_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.TallyListDataView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)

        tally_id, tally_name, created_date, modified_formatted_date,\
            admin_view_link, edit_link = json.loads(
                response.content.decode())['data'][0]

        self.assertEquals(
            admin_view_link,
            f'<a href="/super-administrator/{tally.id}/"'
            ' class ="btn btn-default btn-small">Admin View</a>')
        self.assertEquals(
            edit_link,
            f'<a href="/tally-manager/update-tally/{tally.id}/"'
            ' class ="btn btn-default btn-small">Edit</a>')
        self.assertEquals(tally_id, str(tally.id))
        self.assertEquals(tally_name, tally.name)
        self.assertEquals(created_date, str(tally.created_date))
        self.assertEquals(
            modified_formatted_date,
            tally.modified_date.strftime('%a, %d %b %Y %H:%M:%S %Z'))
