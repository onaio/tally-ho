from django.contrib.auth.models import User
from django.db import models
import reversion

from tally_system.apps.tally.models.result_form import ResultForm
from tally_system.libs.models.base_model import BaseModel


class Archive(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm)
    user = models.ForeignKey(User)


reversion.register(Archive)
