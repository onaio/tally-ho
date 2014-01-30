from django.db import models

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enum.form_state import FormState


class ResultForm(BaseModel):
    race1 = models.ForeignKey('Race')
    race2 = models.ForeignKey('Race')
    center = models.ForeignKey('Center')

    barcode = models.PositiveIntegerField()
    name = models.CharField()
    office = models.CharField()
    serial_number = models.PositiveIntegerField()
    station_number = models.PositiveSmallIntegerField()
    form_state = models.EnumField(FormState)
