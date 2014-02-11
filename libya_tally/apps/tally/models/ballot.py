from django.db import models
from django_enumfield import enum
import reversion

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.race_type import RaceType


class Ballot(BaseModel):
    class Meta:
        app_label = 'tally'

    number = models.PositiveSmallIntegerField()
    race_type = enum.EnumField(RaceType)

    @property
    def race_type_name(self):
        return dict(RaceType.choices())[self.race_type]


reversion.register(Ballot)
