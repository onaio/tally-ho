from django.db import models
from django_enumfield import enum

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.race_type import RaceType


class Candidate(BaseModel):
    class Meta:
        app_label = 'tally'

    race = models.OneToOneField('Race')
    sub_constituency = models.ForeignKey('SubConstituency')

    full_name = models.TextField()
    race_type = enum.EnumField(RaceType)
