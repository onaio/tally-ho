from libya_tally.libs.permissions import groups
from libya_tally.apps.tally.views.home import HomeView
from libya_tally.libs.tests.test_base import TestBase


class TestHomeView(TestBase):
    def setUp(self):
        self.view = HomeView.as_view()

    def test_home_page(self):
        request = self._get_request()
        response = self.view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/?next=/', response['Location'])
        self._create_and_login_user()
        response = self.view(self.request)
        self.assertContains(response, 'Dashboard')
        self.assertIn('/accounts/logout/', response.content)

    def test_intake_clerk_is_redirected(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/intake', response['location'])
