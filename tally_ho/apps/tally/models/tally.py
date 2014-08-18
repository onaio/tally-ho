from django.db import models

from tally_ho.libs.modesl.base_model import BaseModel


class Tally(BaseModel):
    class Meta:
        app_label = 'tally'

    name = models.CharField(max_length=255, null=False, blank=False)
    active = models.BooleanField(default=True)
    modified_date = models.DateTime(null=False, blank=False)
