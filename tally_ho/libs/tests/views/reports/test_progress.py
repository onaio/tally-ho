from django.core.exceptions import ImproperlyConfigured

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import create_result_form, \
    create_center, create_tally, create_reconciliation_form, TestBase
from tally_ho.libs.reports import progress


class TestProgress(TestBase):
    def setUp(self):
        self.barcode = 7
        self.center = create_center()
        self._create_and_login_user()
        self.tally = create_tally()
        self.tally.users.add(self.user)

        create_result_form(
            center=self.center, station_number=1,
            barcode=1, serial_number=1, form_state=FormState.UNSUBMITTED)
        create_result_form(
            center=self.center, station_number=2,
            barcode=2, serial_number=2, form_state=FormState.INTAKE)
        create_result_form(
            center=self.center, station_number=3,
            barcode=3, serial_number=3, form_state=FormState.CLEARANCE)
        create_result_form(
            center=self.center, station_number=4,
            barcode=4, serial_number=4, form_state=FormState.DATA_ENTRY_1)
        create_result_form(
            center=self.center, station_number=5,
            barcode=5, serial_number=5, form_state=FormState.DATA_ENTRY_2)
        create_result_form(
            center=self.center, station_number=6,
            barcode=6, serial_number=6, form_state=FormState.CORRECTION)
        create_result_form(
            center=self.center,
            station_number=7,
            barcode=self.barcode,
            serial_number=7,
            form_state=FormState.QUALITY_CONTROL,
            tally=self.tally)
        create_result_form(
            center=self.center, station_number=8,
            barcode=8, serial_number=8, form_state=FormState.AUDIT)

        self.center_2 = create_center(code=2, office_name='office2')

        create_result_form(
            center=self.center_2, station_number=9,
            barcode=9, serial_number=9, form_state=FormState.UNSUBMITTED)
        create_result_form(
            center=self.center_2, station_number=10,
            barcode=10, serial_number=10, form_state=FormState.ARCHIVED)

        self.assertEqual(ResultForm.objects.count(), 10)

    def test_progress_report(self):
        report = progress.ExpectedProgressReport()
        report.queryset = None
        report.filtered_queryset = None
        with self.assertRaises(ImproperlyConfigured):
            report.total
        with self.assertRaises(ImproperlyConfigured):
            report.number

    def test_expected_progress_report(self):
        report = progress.ExpectedProgressReport()
        self.assertEqual(report.number, 10)
        self.assertEqual(report.total, 10)
        self.assertEqual(report.percentage, 100.0)

    def test_intaken_progress_report(self):
        report = progress.IntakenProgressReport()
        self.assertEqual(report.number, 8)
        self.assertEqual(report.total, 10)
        self.assertEqual(report.percentage, 80)

    def test_archived_progress_report(self):
        report = progress.ArchivedProgressReport()
        self.assertEqual(report.number, 1)
        self.assertEqual(report.total, 10)
        self.assertEqual(report.percentage, 10)

    def test_clearance_progress_report(self):
        report = progress.ClearanceProgressReport()
        self.assertEqual(report.number, 1)
        self.assertEqual(report.total, 10)
        self.assertEqual(report.percentage, 10)

    def test_audit_progress_report(self):
        report = progress.AuditProgressReport()
        self.assertEqual(report.number, 1)
        self.assertEqual(report.total, 10)
        self.assertEqual(report.percentage, 10)

    def test_not_receieved_progress_report(self):
        report = progress.NotRecievedProgressReport()
        self.assertEqual(report.number, 2)
        self.assertEqual(report.total, 10)
        self.assertEqual(report.percentage, 20)

    def test_progress_for_office(self):
        report = progress.ExpectedProgressReport()
        report = report.for_center_office(self.center_2.office)
        self.assertEqual(report.number, 2)
        self.assertEqual(report.total, 2)
        self.assertEqual(report.percentage, 100.0)

    def test_valid_votes_per_office(self):
        result_form = ResultForm.objects.get(barcode=self.barcode)
        create_reconciliation_form(result_form, self.user)
        report = progress.ValidVotesProgressReport(self.tally.id)
        valid_votes = report.for_center_office(
            self.center.office, query_valid_votes=True)
        self.assertEqual(valid_votes, 1)

    def test_zero_valid_votes_per_office(self):
        report = progress.ValidVotesProgressReport(self.tally.id)
        valid_votes = report.for_center_office(
            self.center.office, query_valid_votes=True)
        self.assertEqual(valid_votes, 0)
