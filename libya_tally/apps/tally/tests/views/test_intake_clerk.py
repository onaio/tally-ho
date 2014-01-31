from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally import views
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import TestBase


class TestIntakeClerkView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = views.IntakeClerkView.as_view()
        self._create_permission_groups()

    def _common_view_tests(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            self.view(request)
        self._create_and_login_user()
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            self.view(request)
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        response = self.view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_intake_page(self):
        response = self._common_view_tests()
        self.assertContains(response, '<h1>Intake Dashboard</h1>')
        self.assertIn('"/Intake/CenterDetails"', response.content)

    def test_center_detail_view(self):
        self.view = views.CenterDetailView.as_view()
        response = self._common_view_tests()
        self.assertContains(response, 'Double Enter Center Details')
        self.assertIn('<form id="barcode_form"', response)
