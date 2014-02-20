from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.race_type import RaceType


class Ballot(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['number']

    number = models.PositiveSmallIntegerField()
    race_type = enum.EnumField(RaceType)

    @property
    def race_type_name(self):
        if self.sc_general.all() and self.sc_general.all()[0].ballot_component:
            return _('General and Component')

        return RaceType.label(self.race_type)

    def __unicode__(self):
        return self.number


reversion.register(Ballot)
