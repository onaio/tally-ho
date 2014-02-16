from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.models.reconciliation_form import\
    ReconciliationForm
from libya_tally.apps.tally.views import corrections as views
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_result_form,\
    create_candidate, create_center, create_station, TestBase,\
    create_recon_forms


def create_results(result_form, vote1=1, vote2=1, race_type=RaceType.GENERAL):
    code = '12345'
    center = create_center(code)
    create_station(center)
    ballot = result_form.ballot
    candidate_name = 'candidate name'
    candidate = create_candidate(ballot, candidate_name, race_type)

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


class TestCorrections(TestBase):
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

    def test_corrections_barcode_does_not_exist(self):
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
        create_recon_forms(result_form)
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
        self.assertEqual(
            ReconciliationForm.objects.filter(
                active=True,
                result_form=result_form,
                entry_version=EntryVersion.FINAL).count(), 1)
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.QUALITY_CONTROL)

    def test_corrections_general_post_corrections(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=2, vote2=3)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2)
        session = {'result_form': result_form.pk}
        post_data = {
            'candidate_general_%s' % result_form.results.all()[
                0].candidate.pk: 2,
            'result_form': result_form.pk,
            'submit_corrections': 'submit corrections'
        }
        request = self.factory.post('/', post_data)
        request.session = session
        request.user = self.user
        response = view(request)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.QUALITY_CONTROL)
        self.assertEqual(response.status_code, 302)
        self.assertIn('corrections/success', response['location'])

    def test_corrections_general_post_reject(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_recon_forms(result_form)
        create_results(result_form, vote1=2, vote2=3)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2)
        session = {'result_form': result_form.pk}
        post_data = {
            'candidate_%s' % result_form.results.all()[0].candidate.pk: 2,
            'result_form': result_form.pk,
            'reject': 'reject'
        }
        request = self.factory.post('/', post_data)
        request.session = session
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/corrections', response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)

        for result in updated_result_form.results.all():
            self.assertEqual(result.active, False)

        for recon in updated_result_form.reconciliationform_set.all():
            self.assertEqual(recon.active, False)

        self.assertEqual(updated_result_form.form_state,
                         FormState.DATA_ENTRY_1)

    def test_corrections_general_post_abort(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=2, vote2=3)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2)
        session = {'result_form': result_form.pk}
        post_data = {
            'candidate_%s' % result_form.results.all()[0].candidate.pk: 2,
            'result_form': result_form.pk,
            'abort': 'reject'
        }
        request = self.factory.post('/', post_data)
        request.session = session
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/corrections', response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)

        for result in updated_result_form.results.all():
            self.assertNotEqual(result.entry_version, EntryVersion.FINAL)

        self.assertEqual(updated_result_form.form_state,
                         FormState.CORRECTION)

    def test_corrections_women_post_corrections(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=2, vote2=3, race_type=RaceType.WOMEN)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2)
        session = {'result_form': result_form.pk}
        post_data = {
            'candidate_women_%s' % result_form.results.all()[
                0].candidate.pk: 2,
            'result_form': result_form.pk,
            'submit_corrections': 'submit corrections'
        }
        request = self.factory.post('/', post_data)
        request.session = session
        request.user = self.user
        response = view(request)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.QUALITY_CONTROL)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/corrections/success', response['location'])

    def test_corrections_women_post_reject(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=2, vote2=3, race_type=RaceType.WOMEN)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2)
        session = {'result_form': result_form.pk}
        post_data = {
            'candidate_women_%s' % result_form.results.all()[
                0].candidate.pk: 2,
            'result_form': result_form.pk,
            'reject': 'reject'
        }
        request = self.factory.post('/', post_data)
        request.session = session
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/corrections', response['location'])
        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.DATA_ENTRY_1)

    def test_recon_get(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=2, vote2=3, race_type=RaceType.WOMEN)
        create_recon_forms(result_form)

        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(
            Result.objects.filter(result_form=result_form).count(), 2)
        session = {'result_form': result_form.pk}
        request = self.factory.get('/')
        request.session = session
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reconciliation')

    def test_recon_post(self):
        view = views.CorrectionRequiredView.as_view()
        result_form = create_result_form(form_state=FormState.CORRECTION)
        create_results(result_form, vote1=2, vote2=2, race_type=RaceType.WOMEN)
        create_recon_forms(result_form)

        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        self.assertEqual(ReconciliationForm.objects.filter(
            result_form=result_form).count(), 2)

        session = {'result_form': result_form.pk}
        ballot_from_val = 2
        sorted_counted_val = 3
        data = {'submit_corrections': 1,
                'ballot_number_from': ballot_from_val,
                'number_sorted_and_counted': sorted_counted_val}
        data.update(session)
        request = self.factory.post('/', data=data)
        request.session = session
        request.user = self.user
        response = view(request)
        final_form = ReconciliationForm.objects.filter(
            result_form=result_form, entry_version=EntryVersion.FINAL)[0]

        self.assertEqual(final_form.ballot_number_from, ballot_from_val)
        self.assertEqual(final_form.number_sorted_and_counted,
                         sorted_counted_val)
        self.assertEqual(final_form.result_form, result_form)
        self.assertEqual(final_form.entry_version,
                         EntryVersion.FINAL)
        self.assertEqual(final_form.user, self.user)
        self.assertEqual(response.status_code, 302)

        updated_result_form = ResultForm.objects.get(pk=result_form.pk)
        self.assertEqual(updated_result_form.form_state,
                         FormState.QUALITY_CONTROL)
        self.assertIn('corrections/success', response['location'])

    def test_confirmation_get(self):
        result_form = create_result_form(form_state=FormState.QUALITY_CONTROL)
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.CORRECTIONS_CLERK)
        view = views.ConfirmationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quality Control')
        self.assertContains(response, reverse('corrections-clerk'))
