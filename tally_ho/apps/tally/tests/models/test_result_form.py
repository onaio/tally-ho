from tally_ho.apps.tally.models.result_form import \
    sanity_check_final_results
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import create_reconciliation_form,\
    create_result_form, create_result, create_candidates, create_audit,\
    TestBase


class TestResultForm(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_quality_control(self):
        """Test result form quality control"""
        result_form = create_result_form()
        quality_control = QualityControl.objects.create(
            result_form=result_form,
            user=self.user)
        QualityControl.objects.create(
            result_form=result_form,
            user=self.user,
            active=False)

        self.assertEqual(result_form.qualitycontrol, quality_control)

    def test_reconciliation_match(self):
        """Test result form reconciliation match"""
        result_form = create_result_form()
        create_reconciliation_form(result_form, self.user)
        re_form = create_reconciliation_form(result_form, self.user)
        re_form.entry_version = EntryVersion.DATA_ENTRY_2
        re_form.save()

        self.assertTrue(result_form.reconciliation_match)

    def test_sanity_check_results(self):
        """Test sanity checks for final results"""
        votes = 12
        result_form = create_result_form(form_state=FormState.ARCHIVED)
        create_candidates(result_form, votes=votes, user=self.user,
                          num_results=1)
        for result in result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form, result.candidate, self.user, votes)
        self.assertEqual(result_form.results_final.filter().count(), 4)
        sanity_check_final_results(result_form)
        self.assertEqual(result_form.results_final.filter().count(), 2)

    def test_audit_quarantine_check_name_property_method(self):
        """Test audit quarantine check name property method"""
        result_form = create_result_form()
        quarantine_check = QuarantineCheck.objects.create(
            user=self.user,
            name='1',
            method='1',
            value=1)
        audit = create_audit(result_form, self.user)
        audit.quarantine_checks.add(quarantine_check)
        self.assertQuerysetEqual(
            result_form.audit_quaritine_checks,
            map(repr, audit.quarantine_checks.all().values('name'))
        )
