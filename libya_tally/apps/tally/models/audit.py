from django.contrib.auth.models import User
from django.db import models

from libya_tally.apps.tally.models.quarantine_check import QuarantineCheck
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel


class Audit(BaseModel):
    class Meta:
        app_label = 'tally'

    quarantine_check = models.ForeignKey(QuarantineCheck)
    result_form = models.ForeignKey(ResultForm)
    supervisor = models.ForeignKey(User, related_name='audit_user')
    user = models.ForeignKey(User)

    recommendation = models.TextField()
