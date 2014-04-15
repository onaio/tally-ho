from tally_ho.apps.tally.models.result_form import \
    sanity_check_final_results
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.tests.test_base import create_reconciliation_form,\
    create_result_form, create_result, create_candidates, TestBase


class TestResultForm(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_quality_control(self):
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
        result_form = create_result_form()
        create_reconciliation_form(result_form, self.user)
        re_form = create_reconciliation_form(result_form, self.user)
        re_form.entry_version = EntryVersion.DATA_ENTRY_2
        re_form.save()

        self.assertTrue(result_form.reconciliation_match)

    def test_sanity_check_results(self):
        votes = 12
        result_form = create_result_form()
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
