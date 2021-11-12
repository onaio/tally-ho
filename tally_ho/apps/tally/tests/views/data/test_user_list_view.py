import json
from django.test import RequestFactory

from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.views.data import user_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally, TestBase


class TestUserListView(TestBase):
    """
    Test user list class base views.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_user_list_view(self):
        """
        Test that user list view template is rendered correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.UserListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Name")
        self.assertContains(response, "Email")
        self.assertContains(response, "First Name")
        self.assertContains(response, "Last Name")
        self.assertContains(response, "Tally Name")
        self.assertContains(response, "Date Joined")

    def test_user_list_data_view(self):
        """
        Test that user list data view returns correct data
        """
        tally = create_tally()
        tally.users.add(self.user)
        audit_supervisor_user =\
            UserProfile.objects.create(
                username='audit_supervisor',
                password='password',
                first_name='audit',
                last_name='supervisor')
        self._add_user_to_group(audit_supervisor_user,
                                groups.AUDIT_SUPERVISOR)
        view = views.UserListDataView.as_view()
        request = self.factory.get('/user-list/user')
        request.user = self.user
        response = view(request)

        username, _, first_name, last_name,\
            _, date_joined, edit_link = json.loads(
                response.content.decode())['data'][0]

        self.assertEquals(
            edit_link,
            f'<a href="/tally-manager/edit-user/user/\
                {audit_supervisor_user.id}/"'
            ' class="btn btn-default btn-small">Edit</a>')
        self.assertEquals(username, audit_supervisor_user.username)
        self.assertEquals(first_name, audit_supervisor_user.first_name)
        self.assertEquals(last_name, audit_supervisor_user.last_name)
        self.assertEquals(date_joined,
                          audit_supervisor_user.date_joined.strftime(
                              '%a, %d %b %Y %H:%M:%S %Z'))
