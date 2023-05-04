from django.db import models
import reversion

from tally_ho.libs.models.base_model import BaseModel


class ElectrolRace(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['code']
        unique_together = (('type', 'code'))
    type = models.CharField(max_length=256, null=True)
    code = models.PositiveIntegerField()
    ballot_name = models.CharField(max_length=256, null=True)


reversion.register(ElectrolRace)
