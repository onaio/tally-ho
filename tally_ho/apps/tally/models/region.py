import reversion
from django.db import models

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.base_model import BaseModel


class Region(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['name']
        unique_together = ('name', 'tally')

    name = models.CharField(max_length=255)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='regions',
                              on_delete=models.PROTECT)

    def __str__(self):
        return self.name


reversion.register(Region)
