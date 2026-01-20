import json
from django.core.exceptions import PermissionDenied
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
        request.session = {}
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
        audit_user =\
            UserProfile.objects.create(
                username='audit_supervisor',
                first_name='audit',
                last_name='supervisor')
        self._add_user_to_group(audit_user,
                                groups.AUDIT_SUPERVISOR)
        view = views.UserListDataView.as_view()
        request = self.factory.get('/user-list/user')
        request.user = self.user
        response = view(request)

        username, _, first_name, last_name,\
            _, date_joined, edit_link = json.loads(
                response.content.decode())['data'][0]

        self.assertEqual(
            edit_link,
            f'<a href="/tally-manager/edit-user/user/{audit_user.id}/"'
            ' class="btn btn-default btn-small">Edit</a>')
        self.assertEqual(username, audit_user.username)
        self.assertEqual(first_name, audit_user.first_name)
        self.assertEqual(last_name, audit_user.last_name)
        self.assertEqual(date_joined,
                          audit_user.date_joined.strftime(
                              '%a, %d %b %Y %H:%M:%S %Z'))

    def test_user_list_view_tally_manager_role(self):
        """
        Test that super admin can access tally-manager role list view.
        """
        view = views.UserListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, role='tally-manager')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tally Managers List")
        self.assertContains(response, "New Tally Manager")

    def test_user_list_view_admin_role(self):
        """
        Test that admin role shows Administrators List.
        """
        view = views.UserListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, role='admin')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administrators List")
        self.assertContains(response, "New Administrator")

    def test_user_list_data_view_filters_tally_managers(self):
        """
        Test that user list data view filters by TALLY_MANAGER group
        when role is tally-manager.
        """
        # Create a tally manager user
        tm_user = UserProfile.objects.create(
            username='test_tally_manager',
            first_name='Test',
            last_name='TallyManager')
        self._add_user_to_group(tm_user, groups.TALLY_MANAGER)

        # Create a regular user (should not appear)
        regular_user = UserProfile.objects.create(
            username='regular_user',
            first_name='Regular',
            last_name='User')
        self._add_user_to_group(regular_user, groups.AUDIT_SUPERVISOR)

        view = views.UserListDataView.as_view()
        request = self.factory.get('/user-list/tally-manager')
        request.user = self.user
        response = view(request, role='tally-manager')

        data = json.loads(response.content.decode())['data']

        # Should only contain tally manager users
        usernames = [row[0] for row in data]
        self.assertIn('test_tally_manager', usernames)
        self.assertNotIn('regular_user', usernames)

    def test_user_list_data_view_filters_admins(self):
        """
        Test that user list data view filters by SUPER_ADMINISTRATOR group
        when role is admin.
        """
        # Create another super admin
        admin_user = UserProfile.objects.create(
            username='another_admin',
            first_name='Another',
            last_name='Admin')
        self._add_user_to_group(admin_user, groups.SUPER_ADMINISTRATOR)

        # Create a tally manager (should not appear)
        tm_user = UserProfile.objects.create(
            username='tm_user',
            first_name='TM',
            last_name='User')
        self._add_user_to_group(tm_user, groups.TALLY_MANAGER)

        view = views.UserListDataView.as_view()
        request = self.factory.get('/user-list/admin')
        request.user = self.user
        response = view(request, role='admin')

        data = json.loads(response.content.decode())['data']

        # Should contain admin users
        usernames = [row[0] for row in data]
        self.assertIn('another_admin', usernames)
        self.assertNotIn('tm_user', usernames)


class TestUserListViewPermissions(TestBase):
    """
    Test permission guards for user list views.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()

    def test_tally_manager_cannot_access_tally_manager_role(self):
        """
        Test that TALLY_MANAGER users cannot access tally-manager role list.
        """
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

        view = views.UserListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        with self.assertRaises(PermissionDenied):
            view(request, role='tally-manager')

    def test_super_admin_can_access_tally_manager_role(self):
        """
        Test that SUPER_ADMINISTRATOR users can access tally-manager role list.
        """
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

        view = views.UserListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        response = view(request, role='tally-manager')
        self.assertEqual(response.status_code, 200)

    def test_tally_manager_can_access_admin_role(self):
        """
        Test that TALLY_MANAGER users can access admin role list.
        """
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

        view = views.UserListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        response = view(request, role='admin')
        self.assertEqual(response.status_code, 200)

    def test_tally_manager_can_access_user_role(self):
        """
        Test that TALLY_MANAGER users can access user role list.
        """
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

        view = views.UserListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        response = view(request, role='user')
        self.assertEqual(response.status_code, 200)
