from django.contrib.auth.models import User
from django.db import models

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel


class QualityControl(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.OneToOneField(ResultForm)
    user = models.ForeignKey(User)

    passed_general = models.NullBooleanField()
    passed_reconciliation = models.NullBooleanField()
    passed_womens = models.NullBooleanField()
