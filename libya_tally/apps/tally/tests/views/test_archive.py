from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.views import archive as views
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_result_form, TestBase


class TestArchive(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()

    def _common_view_tests(self, view, session={}):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            view(request)
        self._create_and_login_user()
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request)
        self._add_user_to_group(self.user, groups.ARCHIVE_CLERK)
        request.session = session
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_archive_get(self):
        response = self._common_view_tests(views.ArchiveView.as_view())
        self.assertContains(response, 'Archiving')
        self.assertIn('<form id="result_form"', response.content)

    def test_archive_post(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(form_state=FormState.ARCHIVING)
        self._add_user_to_group(self.user, groups.ARCHIVE_CLERK)
        view = views.ArchiveView.as_view()
        data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=data)
        request.session = {}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('archive/print', response['location'])
