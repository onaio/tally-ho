from django.contrib.auth.models import User
from django.db import models

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel


class Clearance(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm)
    supervisor = models.ForeignKey(User, null=True, related_name='supervisor')
    user = models.ForeignKey(User)

    recommendation = models.TextField()
