from django.contrib.auth.models import User
from django.db import models

from libya_tally.libs.models.base_model import BaseModel


class QuarantineCheck(BaseModel):
    class Meta:
        app_label = 'tally'

    user = models.ForeignKey(User)

    name = models.CharField(max_length=256)
    rule = models.CharField(max_length=256)
