from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views.intake_clerk import IntakeClerkView
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import TestBase


class TestIntakeClerkView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = IntakeClerkView.as_view()
        self._create_permission_groups()

    def test_intake_page(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            response = self.view(request)
        self._create_and_login_user()
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            response = self.view(request)
        self._add_user_to_group(self.user, groups.INTAKE_CLERK)
        response = self.view(request)
        self.assertContains(response, '<h1>Intake Dashboard</h1>')
        self.assertIn('/accounts/logout/', response.content)
