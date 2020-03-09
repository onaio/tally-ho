from django.utils import timezone

from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import create_result_form,\
    create_result_form_stats, TestBase


class TestResultFormStats(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_result_form_stats(self):
        result_form = create_result_form()
        start_time = timezone.now()
        ten_minutes = 10
        end_time = start_time + timezone.timedelta(minutes=ten_minutes)

        result_form_stats = create_result_form_stats(
            form_state=FormState.AUDIT,
            start_time=start_time,
            end_time=end_time,
            user=self.user,
            result_form=result_form,
            approved_by_supervisor=True
        )

        self.assertEqual(result_form_stats.start_time, start_time)
        self.assertEqual(result_form_stats.end_time, end_time)

        time_elapsed = {'hours': 0, 'minutes': ten_minutes, 'seconds': 0}
        self.assertEqual(result_form_stats.get_time_elapsed, time_elapsed)
