from django.contrib.auth.models import User
from django.db import models
import reversion

from libya_tally.libs.models.base_model import BaseModel


class QuarantineCheck(BaseModel):
    class Meta:
        app_label = 'tally'

    user = models.ForeignKey(User, null=True)

    name = models.CharField(max_length=256, unique=True)
    method = models.CharField(max_length=256, unique=True)
    value = models.FloatField()


reversion.register(QuarantineCheck)
