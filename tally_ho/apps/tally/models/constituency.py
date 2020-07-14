from django.db import models
import reversion

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.center import Center
from tally_ho.libs.models.base_model import BaseModel


class Constituency(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['name']
        unique_together = ('name', 'tally')

    name = models.CharField(max_length=255)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='constituency',
                              on_delete=models.PROTECT)

    def __str__(self):
        return self.name


reversion.register(Constituency)
