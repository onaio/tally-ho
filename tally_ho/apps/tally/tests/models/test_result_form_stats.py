from django.utils import timezone

from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_result_form,
    create_result_form_stats,
    create_tally,
)


class TestResultFormStats(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_result_form_stats(self):
        tally = create_tally()
        tally.users.add(self.user)

        result_form =\
            create_result_form(
                name="Example",
                tally=tally,
                form_state=FormState.AUDIT)
        start_time = timezone.now()
        minutes = 65.5
        end_time = start_time + timezone.timedelta(minutes=minutes)

        form_processing_time_in_seconds =\
            (end_time - start_time).total_seconds()

        # Audit supervisor audit review
        audit_supervisor_user =\
            self._create_user('audit_supervisor', 'password')
        self._add_user_to_group(audit_supervisor_user,
                                groups.AUDIT_SUPERVISOR)
        result_form_stats = create_result_form_stats(
            processing_time=form_processing_time_in_seconds,
            user=audit_supervisor_user,
            result_form=result_form,
            reviewed_by_supervisor=True,
            approved_by_supervisor=True
        )

        self.assertTrue(isinstance(result_form_stats, ResultFormStats))
        self.assertEqual(1, ResultFormStats.objects.count())
        self.assertEqual(
            result_form_stats.processing_time,
            form_processing_time_in_seconds)
        self.assertEqual(
            result_form_stats.user,
            audit_supervisor_user)
        self.assertEqual(
            result_form_stats.result_form,
            result_form)
        self.assertEqual(
            result_form_stats.approved_by_supervisor,
            True)
        self.assertEqual(
            result_form_stats.reviewed_by_supervisor,
            True)
