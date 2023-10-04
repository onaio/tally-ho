import json
from django.test import RequestFactory

from tally_ho.apps.tally.views.data import tally_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally, TestBase


class TestTallyListView(TestBase):
    """
    Test tally list class base views.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_tally_list_view(self):
        """
        Test that tally list view template is rendered correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.TallyListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertContains(response, "Tally List")
        self.assertContains(response, "Id")
        self.assertContains(response, "Name")
        self.assertContains(response, "Creation")
        self.assertContains(response, "Last Modification")
        self.assertContains(response, "Administration")
        self.assertContains(response, "Actions")

    def test_tally_list_data_view(self):
        """
        Test that tally list data view returns correct data
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.TallyListDataView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)

        tally_id, tally_name, created_date, modified_formatted_date,\
            admin_view_link, edit_link = json.loads(
                response.content.decode())['data'][0]

        self.assertEqual(
            admin_view_link,
            f'<a href="/super-administrator/{tally.id}/"'
            ' class ="btn btn-default btn-small">Admin View</a>')
        self.assertEqual(
            edit_link,
            f'<a href="/tally-manager/update-tally/{tally.id}/"'
            ' class ="btn btn-default btn-small">Edit</a>')
        self.assertEqual(tally_id, str(tally.id))
        self.assertEqual(tally_name, tally.name)
        self.assertEqual(created_date, str(tally.created_date))
        self.assertEqual(
            modified_formatted_date,
            tally.modified_date.strftime('%a, %d %b %Y %H:%M:%S %Z'))

    def test_tally_list_data_view_valid_search_filter(self):
        """
        Test that tally list data view returns the correct data
        when a valid search filter is applied.
        """
        tally_1 = create_tally(name='example_1_tally')
        create_tally(name='example_2_tally')
        view = views.TallyListDataView.as_view()
        request = self.factory.post('/')
        request.user = self.user
        request.POST = request.POST.copy()
        request.POST['search[value]'] = tally_1.name
        response = view(request)
        data = json.loads(response.content.decode())['data']
        tally_id, tally_name, created_date, modified_formatted_date,\
            admin_view_link, edit_link = data[0]

        self.assertEqual(1, len(data))
        self.assertEqual(
            admin_view_link,
            f'<a href="/super-administrator/{tally_1.id}/"'
            ' class ="btn btn-default btn-small">Admin View</a>')
        self.assertEqual(
            edit_link,
            f'<a href="/tally-manager/update-tally/{tally_1.id}/"'
            ' class ="btn btn-default btn-small">Edit</a>')
        self.assertEqual(tally_id, str(tally_1.id))
        self.assertEqual(tally_name, tally_1.name)
        self.assertEqual(created_date, str(tally_1.created_date))
        self.assertEqual(
            modified_formatted_date,
            tally_1.modified_date.strftime('%a, %d %b %Y %H:%M:%S %Z'))

    def test_tally_list_data_view_invalid_search_filter(self):
        """
        Test that tally list data view returns no data when an invalid
        search filter is applied.
        """
        create_tally(name='example_1_tally')
        create_tally(name='example_2_tally')
        view = views.TallyListDataView.as_view()
        request = self.factory.post('/')
        request.user = self.user
        request.POST = request.POST.copy()
        request.POST['search[value]'] = 'Invalid search text'
        response = view(request)
        json_data = json.loads(response.content.decode())

        self.assertListEqual([], json_data['data'])
        self.assertEqual(2, json_data['recordsTotal'])
