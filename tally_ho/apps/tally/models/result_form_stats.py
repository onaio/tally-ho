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


reversion.register(ResultFormStats)
