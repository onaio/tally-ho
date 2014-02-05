from django.db import models
from django_enumfield import enum

from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.gender import Gender


class Station(BaseModel):
    class Meta:
        app_label = 'tally'

    center = models.ForeignKey(Center, related_name='stations')
    sub_constituency = models.ForeignKey(SubConstituency,
                                         related_name='stations')

    gender = enum.EnumField(Gender)
    registrants = models.PositiveIntegerField(null=True)
    station_number = models.PositiveSmallIntegerField()

    @property
    def gender_name(self):
        return Gender.to_name(self.gender)
