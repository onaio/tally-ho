from django.db import models

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.libs.models.base_model import BaseModel


class SubConstituency(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot_general = models.ForeignKey(Ballot, null=True,
                                       related_name='ballot_general')
    ballot_women = models.ForeignKey(Ballot, null=True,
                                     related_name='ballot_women')
    code = models.PositiveSmallIntegerField()  # aka SubCon number
    component_ballot = models.BooleanField()
    field_office = models.CharField(max_length=256)
    number_of_ballots = models.PositiveSmallIntegerField(null=True)
    races = models.PositiveSmallIntegerField(null=True)
