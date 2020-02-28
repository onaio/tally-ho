from django.db import models
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.base_model import BaseModel


class ResultFormStats(BaseModel):
    class Meta:
        app_label = 'tally'

    form_state = EnumIntegerField(FormState)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)
    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    for_superadmin = models.BooleanField(default=False)
    reviewed_by_supervisor = models.BooleanField(default=False)

    @property
    def get_time_elapsed(self):
        """Calculate time taken to process a result form in minutes and seconds.

        Find the difference between the end time and start time.
        :param start_time: Time the result form started to be processed.
        :param end_time: Time the result form ended to be processed.

        :returns: A dict of rounded time in minutes and seconds.
        """
        one_minute_in_seconds = 60
        time_elapsed =\
            (divmod((self.end_time - self.start_time).total_seconds(),
                    one_minute_in_seconds))
        return {'minutes': round(time_elapsed[0]),
                'seconds':  round(time_elapsed[1])}


reversion.register(ResultFormStats)
