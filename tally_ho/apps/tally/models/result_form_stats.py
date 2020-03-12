from django.db import models
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel


class ResultFormStats(BaseModel):
    class Meta:
        app_label = 'tally'

    processing_time = models.PositiveIntegerField(null=True)
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)
    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    approved_by_supervisor = models.BooleanField(default=False)
    reviewed_by_supervisor = models.BooleanField(default=False)


reversion.register(ResultFormStats)
