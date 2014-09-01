from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.views import archive as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_audit, create_candidates,\
    create_center, create_reconciliation_form, create_result_form,\
    create_station, TestBase
from tally_ho.libs.verify.quarantine_checks import create_quarantine_checks


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
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
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
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
        view = views.ArchiveView.as_view()
        data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=data)
        request.session = {}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('archive/print', response['location'])

    def test_archive_post_supervisor(self):
        self._create_and_login_user()
        barcode = '123456789'
        create_result_form(form_state=FormState.ARCHIVED)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR)
        view = views.ArchiveView.as_view()
        data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=data)
        request.session = {}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('archive/print', response['location'])

    def test_archive_post_quarantine_pass_with_zero_diff(self):
        center = create_center()
        create_station(center)
        create_quarantine_checks()
        self._create_and_login_user()
        barcode = '123456789'
        result_form = create_result_form(
            form_state=FormState.ARCHIVING,
            center=center, station_number=1)
        recon_form = create_reconciliation_form(
            result_form, self.user, number_unstamped_ballots=0)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
        view = views.ArchiveView.as_view()
        data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=data)
        request.session = {}
        request.user = self.user
        response = view(request)
        result_form.reload()

        self.assertEqual(result_form.num_votes,
                         recon_form.number_ballots_expected)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(result_form.form_state, FormState.AUDIT)
        self.assertIsNone(result_form.audit)
        self.assertEqual(result_form.audited_count, 0)
        self.assertIn('archive/print', response['location'])

    def test_archive_post_quarantine_pass_below_tolerance(self):
        center = create_center()
        create_station(center)
        create_quarantine_checks()
        self._create_and_login_user()
        barcode = '123456789'
        result_form = create_result_form(
            form_state=FormState.ARCHIVING,
            center=center, station_number=1)
        recon_form = create_reconciliation_form(
            result_form, self.user, number_ballots_inside_box=21,
            number_unstamped_ballots=0)
        create_candidates(result_form, self.user, votes=1, num_results=10)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
        view = views.ArchiveView.as_view()
        data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=data)
        request.session = {}
        request.user = self.user
        response = view(request)
        result_form.reload()

        self.assertEqual(result_form.num_votes,
                         recon_form.number_ballots_expected)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(result_form.form_state, FormState.AUDIT)
        self.assertTrue(result_form.audit)
        self.assertEqual(result_form.audit.quarantine_checks.count(), 1)
        self.assertEqual(
            result_form.audit.quarantine_checks.all()[0].name[:9], 'Trigger 1')
        self.assertEqual(result_form.audited_count, 1)
        self.assertIn('archive/print', response['location'])

    def test_archive_post_quarantine(self):
        center = create_center()
        create_station(center)
        create_quarantine_checks()
        self._create_and_login_user()
        barcode = '123456789'
        result_form = create_result_form(
            form_state=FormState.ARCHIVING,
            center=center, station_number=1)
        create_reconciliation_form(
            result_form, self.user, number_unstamped_ballots=1000)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
        view = views.ArchiveView.as_view()
        data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=data)
        request.session = {}
        request.user = self.user
        response = view(request)
        result_form.reload()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(result_form.form_state, FormState.AUDIT)
        self.assertTrue(result_form.audit)
        self.assertEqual(result_form.audit.quarantine_checks.count(), 2)
        self.assertEqual(result_form.audit.user, self.user)
        self.assertEqual(result_form.audited_count, 1)
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
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
        view = views.ArchivePrintView.as_view()
        request = self.factory.get('/')
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successful Archive')

    def test_print_success_get_supervisor(self):
        self._create_and_login_user()
        code = '12345'
        station_number = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.ARCHIVED,
                                         center=center,
                                         station_number=station_number)
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR)
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
        audit = create_audit(result_form, self.user)
        audit.quarantine_checks.add(quarantine_check)

        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
        view = views.ArchivePrintView.as_view()
        request = self.factory.get('/')
        request.session = {'result_form': result_form.pk}
        request.user = self.user
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quarantined')

    def test_print_post(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)

        result_form = create_result_form(form_state=FormState.ARCHIVING)
        view = views.ArchivePrintView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.session = data
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/archive/success', response['location'])

        result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_print_post_supervisor(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR)

        result_form = create_result_form(form_state=FormState.ARCHIVED)
        view = views.ArchivePrintView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.session = data
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/archive/success', response['location'])

        result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_confirmation_get(self):
        result_form = create_result_form(form_state=FormState.ARCHIVING)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.QUALITY_CONTROL_ARCHIVE_CLERK)
        view = views.ConfirmationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(request.session.get('result_form'))
        self.assertContains(response, 'Archive')
        self.assertContains(response, reverse('archive'))
