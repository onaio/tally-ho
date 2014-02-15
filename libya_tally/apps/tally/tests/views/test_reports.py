from django.test import RequestFactory

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.views.reports import overview
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_center, \
    create_result_form, TestBase


class TestReportViews(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_form_action_view_post_invalid_audit(self):
        center = create_center()
        create_result_form(
            barcode=1, serial_number=1, form_state=FormState.UNSUBMITTED)
        create_result_form(
            barcode=2, serial_number=2, form_state=FormState.INTAKE)
        create_result_form(
            barcode=3, serial_number=3, form_state=FormState.CLEARANCE)
        create_result_form(
            barcode=4, serial_number=4, form_state=FormState.DATA_ENTRY_1,
            center=center)
        create_result_form(
            barcode=5, serial_number=5, form_state=FormState.DATA_ENTRY_2)
        create_result_form(
            barcode=6, serial_number=6, form_state=FormState.CORRECTION)
        create_result_form(
            barcode=7, serial_number=7, form_state=FormState.QUALITY_CONTROL,
            center=center)
        create_result_form(
            barcode=8, serial_number=8, form_state=FormState.AUDIT)
        create_result_form(
            barcode=9, serial_number=9, form_state=FormState.UNSUBMITTED)
        create_result_form(
            barcode=10, serial_number=10, form_state=FormState.ARCHIVED)
        create_result_form(form_state=FormState.ARCHIVING)
        self.assertEqual(ResultForm.objects.count(), 11)

        request = self._get_request()
        view = overview.OverviewReportView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        response = view(request)
        self.assertContains(response, 'Per Office')
        self.assertContains(response, 'Tally Centre Progress Report')
        self.assertContains(response, "<td>2</td>")
        self.assertContains(response, "<td>18.1818181818</td>")
        self.assertContains(response, "<td>Not Received</td>")
