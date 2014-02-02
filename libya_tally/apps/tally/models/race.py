from django.db import models
from django_enumfield import enum

from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.race_type import RaceType


class Race(BaseModel):
    class Meta:
        app_label = 'tally'

    sub_constituency = models.ManyToManyField(SubConstituency)

    name = models.CharField(max_length=256)
    race_type = enum.EnumField(RaceType)
