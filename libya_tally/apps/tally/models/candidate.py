from django.db import models

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.race_type import RaceType


class Candidate(BaseModel):
    race = models.OneToOneField('Race')
    sub_constituency = models.ForeignKey('SubConstituency')

    full_name = models.CharField()
    race_type = models.EnumField(RaceType)
