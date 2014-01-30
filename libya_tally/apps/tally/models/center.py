from django.db import models

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.center_type import CenterType


class Center(BaseModel):
    sub_constituency = models.ForeignKey('SubConstituency')

    center_type = models.EnumField(CenterType)
    code = models.PositiveIntegerField(unique=True)
    latitude = models.FloatField()
    longitutde = models.FloatField()
    mahalla = models.CharField()
    name = models.CharField(unique=True)
    office = models.CharField()
    region = models.CharField()
    village = models.CharField()
