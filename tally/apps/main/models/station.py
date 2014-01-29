from django.db import models

from tally.libs.models.base_model import BaseModel
from tally.libs.models.enums.gender import Gender


class Station(BaseModel):
    center = models.ForeignKey('Center')
    gender = models.EnumField(Gender)
    number = models.IntegerField()
    registrants = models.IntegerField()
