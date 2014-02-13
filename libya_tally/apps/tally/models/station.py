from django.db import models
from django_enumfield import enum
import reversion

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
        return Gender.label(self.gender)

    @property
    def center_code(self):
        return self.center.code if self.center else None

    @property
    def center_office(self):
        return self.center.office if self.center else None

    @property
    def sub_constituency_code(self):
        return self.sub_constituency.code if self.sub_constituency else None

    @property
    def center_name(self):
        return self.center.name if self.center else None


reversion.register(Station)
