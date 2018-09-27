from django.db import models
import reversion

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.base_model import BaseModel


class Office(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['name']
        unique_together = ('name', 'tally')

    name = models.CharField(max_length=256)
    number = models.IntegerField(null=True)
    tally = models.ForeignKey(Tally, null=True, blank=True, related_name='offices')


reversion.register(Office)
