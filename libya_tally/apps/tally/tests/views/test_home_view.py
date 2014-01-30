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
