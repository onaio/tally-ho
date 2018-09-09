from django.contrib.auth.models import User
from django.db import models
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.base_model import BaseModel


class Archive(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)


reversion.register(Archive)
