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

        return _(RaceType.label(self.race_type))

    @property
    def sub_constituency(self):
        sc = self.sc_general.all() or self.sc_women.all() or\
            self.sc_component.all()

        if sc:
            return sc[0]

    @property
    def component_ballot(self):
        return self.sc_general and self.sc_general.all() and\
            self.sc_general.all()[0].ballot_component

    def __unicode__(self):
        return self.number


reversion.register(Ballot)
