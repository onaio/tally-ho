from django.db import models
import reversion

from tally_ho.libs.models.base_model import BaseModel


class Office(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['name']

    name = models.CharField(max_length=256, unique=True)
    number = models.IntegerField(null=True)


reversion.register(Office)
