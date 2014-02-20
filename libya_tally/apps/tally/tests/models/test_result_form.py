from libya_tally.apps.tally.models.quality_control import QualityControl
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.tests.test_base import create_reconciliation_form,\
    create_result_form, TestBase


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
