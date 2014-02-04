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
    create_candidate, create_center, create_station, center_data,\
    result_form_data, result_form_data_blank, TestBase


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

    def test_corrctions_page(self):
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
        code = '12345'
        votes = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.CORRECTION)
        ballot = result_form.ballot
        candidate_name = 'candidate name'
        candidate = create_candidate(ballot, candidate_name)

        Result.objects.create(
            candidate=candidate,
            result_form=result_form,
            entry_version=EntryVersion.DATA_ENTRY_1,
            votes=votes)

        Result.objects.create(
            candidate=candidate,
            result_form=result_form,
            entry_version=EntryVersion.DATA_ENTRY_2,
            votes=votes)

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
        code = '12345'
        votes = 1
        center = create_center(code)
        create_station(center)
        result_form = create_result_form(form_state=FormState.CORRECTION)
        ballot = result_form.ballot
        candidate_name = 'candidate name'
        candidate = create_candidate(ballot, candidate_name)

        Result.objects.create(
            candidate=candidate,
            result_form=result_form,
            entry_version=EntryVersion.DATA_ENTRY_1,
            votes=votes)

        Result.objects.create(
            candidate=candidate,
            result_form=result_form,
            entry_version=EntryVersion.DATA_ENTRY_2,
            votes=3)

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
