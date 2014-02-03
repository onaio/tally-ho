from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import corrections as views
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import TestBase


class TestCorrectionView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()

    def _common_view_tests(self, view):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            view(request)
        self._create_and_login_user()
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request)
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_intake_page(self):
        response = self._common_view_tests(views.CorrectionView.as_view())
        self.assertContains(response, 'Correction')
        self.assertIn('<form id="result_form"', response.content)
