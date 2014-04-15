from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.views.home import HomeView, suspicious_error
from tally_ho.libs.tests.test_base import TestBase


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

    def test_suspicious_error(self):
        self._create_and_login_user()
        error_message = "Some Error Message!"
        self.request.session = {'error_message': error_message}
        response = suspicious_error(self.request)
        self.assertContains(response, error_message)
