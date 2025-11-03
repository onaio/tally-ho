from django.db import models
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel

class ResultFormReset(BaseModel):
    class Meta:
        app_label = 'tally'
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)
    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    tally = models.ForeignKey(Tally,
                                on_delete=models.PROTECT,
                                related_name='result_form_resets')
    reason = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.tally_id and self.result_form_id:
            self.tally_id = self.result_form.tally_id
        super().save(*args, **kwargs)

reversion.register(ResultFormReset)
