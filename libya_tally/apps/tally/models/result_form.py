from django.db import models
from django_enumfield import enum

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.form_state import FormState


class ResultForm(BaseModel):
    class Meta:
        app_label = 'tally'

    race1 = models.ForeignKey('Race', related_name='race1')
    race2 = models.ForeignKey('Race', related_name='race2')
    center = models.ForeignKey('Center')

    barcode = models.PositiveIntegerField()
    name = models.CharField(max_length=256)
    office = models.CharField(max_length=256)
    serial_number = models.PositiveIntegerField()
    station_number = models.PositiveSmallIntegerField()
    form_state = enum.EnumField(FormState)
