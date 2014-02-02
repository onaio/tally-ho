from django.contrib.auth.models import User
from django.db import models

from libya_tally.apps.tally.models.result import Result
from libya_tally.libs.models.base_model import BaseModel


class Correction(BaseModel):
    class Meta:
        app_label = 'tally'

    result = models.ForeignKey(Result)
    user = models.ForeignKey(User)
