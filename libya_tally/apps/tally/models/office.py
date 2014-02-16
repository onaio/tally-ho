from django.db import models
import reversion

from libya_tally.libs.models.base_model import BaseModel


class Office(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['name']

    name = models.CharField(max_length=256, unique=True)

    def __unicode__(self):
        return self.name


reversion.register(Office)
