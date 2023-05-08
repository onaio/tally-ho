from django.db import models
from django.contrib.postgres.fields import ArrayField
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
    component_ballot_numbers = ArrayField(models.CharField(max_length=200),
                                          blank=True,
                                          null=True)


reversion.register(ElectrolRace)
