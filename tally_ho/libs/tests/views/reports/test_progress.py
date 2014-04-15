from django.core.exceptions import ImproperlyConfigured

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import create_result_form, \
    create_center, TestBase
from tally_ho.libs.reports import progress


class TestArchive(TestBase):
    def setUp(self):
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

    def test_progress_report(self):
        report = progress.ExpectedProgressReport()
        with self.assertRaises(ImproperlyConfigured):
            report.total
        with self.assertRaises(ImproperlyConfigured):
            report.number

    def test_expected_progress_report(self):
        report = progress.ExpectedProgressReport()
        self.assertEqual(report.number, 11)
        self.assertEqual(report.total, 11)
        self.assertEqual(report.percentage, 100.0)

    def test_intaken_progress_report(self):
        report = progress.IntakenProgressReport()
        self.assertEqual(report.number, 8)
        self.assertEqual(report.total, 11)
        self.assertEqual(report.percentage, 72.72727272727273)

    def test_archived_progress_report(self):
        report = progress.ArchivedProgressReport()
        self.assertEqual(report.number, 1)
        self.assertEqual(report.total, 11)
        self.assertEqual(report.percentage, 9.090909090909092)

    def test_clearance_progress_report(self):
        report = progress.ClearanceProgressReport()
        self.assertEqual(report.number, 1)
        self.assertEqual(report.total, 11)
        self.assertEqual(report.percentage, 9.090909090909092)

    def test_audit_progress_report(self):
        report = progress.AuditProgressReport()
        self.assertEqual(report.number, 1)
        self.assertEqual(report.total, 11)
        self.assertEqual(report.percentage, 9.090909090909092)

    def test_not_receieved_progress_report(self):
        report = progress.NotRecievedProgressReport()
        self.assertEqual(report.number, 2)
        self.assertEqual(report.total, 11)
        self.assertEqual(report.percentage, 18.181818181818183)

    def test_progress_for_office(self):
        report = progress.ExpectedProgressReport()
        report = report.for_center_office('1')
        self.assertEqual(report.number, 2)
        self.assertEqual(report.total, 2)
        self.assertEqual(report.percentage, 100.0)
