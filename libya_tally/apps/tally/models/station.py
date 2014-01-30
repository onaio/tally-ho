from django.db import models

from tally.libs.models.base_model import BaseModel
from tally.libs.models.enums.gender import Gender


class Station(BaseModel):
    center = models.ForeignKey('Center')
    sub_constituency = models.ForeignKey('SubConstituency')

    code = models.PositiveSmallIntegerField()  # aka number
    gender = models.EnumField(Gender)
    registrants = models.PositiveIntegerField()
    station_number = models.PositiveIntegerField()
