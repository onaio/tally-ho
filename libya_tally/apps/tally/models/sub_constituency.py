from django.db import models

from libya_tally.libs.models.base_model import BaseModel


class SubConstituency(BaseModel):
    ballot_number_general = models.PositiveSmallIntegerField()
    ballot_number_women = models.PositiveSmallIntegerField()
    code = models.PositiveSmallIntegerField()  # aka SubCon number
    component_ballot = models.BooleanField()
    field_office = models.CharField()
    number_of_ballots = models.PositiveSmallIntegerField()
    races = models.PositiveSmallIntegerField()
