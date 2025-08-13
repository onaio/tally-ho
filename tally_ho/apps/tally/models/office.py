import reversion
from django.db import models

from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.base_model import BaseModel


class Office(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['name']
        unique_together = ('name', 'tally', 'region')

    name = models.CharField(max_length=255)
    number = models.IntegerField(null=True)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='offices',
                              on_delete=models.PROTECT)
    region = models.ForeignKey(Region,
                               null=True,
                               blank=True,
                               related_name='offices',
                               on_delete=models.PROTECT)

    def __str__(self):
        return '%s - %s' % (self.number, self.name)


reversion.register(Office)
