from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.libs.tests.test_base import create_candidates,\
    create_result_form, TestBase


class TestQualityControl(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_reviews_passed(self):
        result_form = create_result_form()
        create_candidates(result_form, self.user)
        quality_control = QualityControl.objects.create(
            result_form=result_form,
            user=self.user)

        self.assertFalse(quality_control.reviews_passed)

        quality_control.passed_general = True
        quality_control.save()
        self.assertFalse(quality_control.reviews_passed)

        quality_control.passed_reconciliation = True
        quality_control.save()
        self.assertFalse(quality_control.reviews_passed)

        quality_control.passed_women = True
        quality_control.save()
        self.assertTrue(quality_control.reviews_passed)
