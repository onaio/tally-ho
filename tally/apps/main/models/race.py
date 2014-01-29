from django.db import models

from tally.libs.models.base_model import BaseModel
from tally.libs.models.enums.race_type import RaceType


class Race(BaseModel):
    name = models.CharField()
    race_type = models.EnumField(RaceType)
