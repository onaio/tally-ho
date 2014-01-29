from django.test import TestCase
from django.test import RequestFactory

from tally.apps.main.views.home import HomeView


class TestHomeView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = HomeView.as_view()

    def test_home_page(self):
        request = self.factory.get('/')
        response = self.view(request)
        self.assertContains(response, 'Home')
