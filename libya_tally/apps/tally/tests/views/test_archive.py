from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.views import corrections as views
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_result_form, \
    create_candidate, create_center, create_station, TestBase


def create_results(result_form, vote1=1, vote2=1):
    code = '12345'
    center = create_center(code)
    create_station(center)
    ballot = result_form.ballot
    candidate_name = 'candidate name'
    candidate = create_candidate(ballot, candidate_name)

    Result.objects.create(
        candidate=candidate,
        result_form=result_form,
        entry_version=EntryVersion.DATA_ENTRY_1,
        votes=vote1)

    Result.objects.create(
        candidate=candidate,
        result_form=result_form,
        entry_version=EntryVersion.DATA_ENTRY_2,
        votes=vote2)


class TestCorrectionView(TestBase):
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
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        request.session = session
        response = view(request)
        response.render()
        self.assertIn('/accounts/logout/', response.content)
        return response

    def test_corrections_page(self):
        response = self._common_view_tests(views.CorrectionView.as_view())
        self.assertContains(response, 'Correction')
        self.assertIn('<form id="result_form"', response.content)

    def test_corrections_barcode_length(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        short_length_barcode_data = {'barcode': '1223', 'barcode_copy': '1223'}
        request = self.factory.post('/', data=short_length_barcode_data)
        request.user = self.user
        response = view(request)
        self.assertContains(response,
                            u'Ensure this value has at least 9 characters')

    def test_corrections_barcode_not_equal(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {'barcode': '123453789', 'barcode_copy': '123456789'}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        response = view(request)
        self.assertContains(response, 'Barcodes do not match')

    def test_ccorrections_barcode_does_not_exist(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {'barcode': '123456789', 'barcode_copy': '123456789'}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        response = view(request)
        self.assertContains(response, 'Barcode does not exist')

    def test_corrections_redirects_to_corrections_match(self):
        barcode = '123456789'
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=1, vote2=1)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('corrections/match', response['location'])

    def test_corrections_redirects_to_corrections_required(self):
        barcode = '123456789'
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=1, vote2=3)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.CorrectionView.as_view()
        barcode_data = {'barcode': barcode, 'barcode_copy': barcode}
        request = self.factory.post('/', data=barcode_data)
        request.user = self.user
        request.session = {}
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('corrections/required', response['location'])

    def test_corrections_match_page(self):
        result_form = create_result_form(form_state=FormState.CORRECTION)
        session = {'result_form': result_form.pk}
        response = self._common_view_tests(
            views.CorrectionMatchView.as_view(), session=session)
        string_matches = [
            'Corrections', 'Form Race Type:', 'Form Entries Match',
            'Pass to Quality Control', '<input type="hidden" '
            'name="result_form" value="%s">' % result_form.pk]
        for check_str in string_matches:
            self.assertContains(response, check_str)

    def test_corrections_match_pass_to_quality_control(self):
        view = views.CorrectionMatchView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=3, vote2=3)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2)
        session = {'result_form': result_form.pk}
        data = {'result_form': result_form.pk,
                'pass_to_quality_control': 'true'}
        request = self.factory.post('/', data=data)
        request.session = session
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 3)
        self.assertEqual(
            Result.objects.filter(result_form=result_form,
                                  entry_version=EntryVersion.FINAL).count(), 1)
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.QUALITY_CONTROL)
