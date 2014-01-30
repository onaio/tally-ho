from django.db import models
from django_enumfield import enum

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.form_type import FormType


class Center(BaseModel):
    class Meta:
        app_label = 'tally'

    sub_constituency = models.ForeignKey('SubConstituency')

    center_type = enum.EnumField(FormType)
    code = models.PositiveIntegerField(unique=True)
    latitude = models.FloatField()
    longitutde = models.FloatField()
    mahalla = models.TextField()
    name = models.TextField(unique=True)
    office = models.TextField()
    region = models.TextField()
    village = models.TextField()
