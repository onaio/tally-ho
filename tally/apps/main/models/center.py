from django.db import models

from tally.libs.models.base_model import BaseModel
from tally.libs.models.enums.center_type import CenterType


class Center(BaseModel):
    code = models.IntegerField(unique=True)
    latitude = models.FloatField()
    longitutde = models.FloatField()
    female_registrants = models.IntegerField()
    mahalla = models.CharField()
    male_registrants = models.IntegerField()
    name = models.CharField(unique=True)
    number = models.IntegerField(unique=True)
    region = models.CharField()
    center_type = models.EnumField(CenterType)
    village = models.CharField()
