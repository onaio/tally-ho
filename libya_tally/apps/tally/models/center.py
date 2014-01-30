from django.db import models

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.center_type import CenterType


class Center(BaseModel):
    center_type = models.EnumField(CenterType)
    code = models.PositiveIntegerField(unique=True)
    female_registrants = models.PositiveIntegerField()
    latitude = models.FloatField()
    longitutde = models.FloatField()
    mahalla = models.CharField()
    male_registrants = models.PositiveIntegerField()
    name = models.CharField(unique=True)
    number = models.PositiveIntegerField(unique=True)
    region = models.CharField()
    village = models.CharField()
