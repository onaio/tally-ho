from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.models.audit import Audit
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.models.quarantine_check import QuarantineCheck
from libya_tally.apps.tally.views import archive as views
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_center,\
    create_result_form, create_station, TestBase


class TestArchive(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()

    def _common_view_tests(self, view, session={}):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/accounts/login/?next=/', response['location'])
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

    def test_print_success_get(self):
        self._create_and_login_user()
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.ARCHIVING,
                                         center=center,
                                         station_number=station_number)
        self._add_user_to_group(self.user, groups.ARCHIVE_CLERK)
        view = views.ArchivePrintView.as_view()
        request = self.factory.get('/')
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successful Archive')

    def test_print_quarantine_get(self):
        self._create_and_login_user()
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.ARCHIVING,
                                         center=center,
                                         station_number=station_number)
        quarantine_check = QuarantineCheck.objects.create(
            user=self.user,
            name='1',
            method='1',
            value=1)
        audit = Audit.objects.create(user=self.user, result_form=result_form)
        audit.quarantine_checks.add(quarantine_check)

        self._add_user_to_group(self.user, groups.ARCHIVE_CLERK)
        view = views.ArchivePrintView.as_view()
        request = self.factory.get('/')
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quarantined')

    def test_print_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.ARCHIVE_CLERK)

        result_form = create_result_form(form_state=FormState.ARCHIVING)
        view = views.ArchivePrintView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.session = data
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/archive', response['location'])

        result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)
