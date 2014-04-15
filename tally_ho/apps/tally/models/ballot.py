from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.race_type import RaceType


class Ballot(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['number']

    COMPONENT_TO_BALLOTS = {
        55: [26, 27, 28],
        56: [29, 30, 31],
        57: [34],
        58: [47],
    }

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
        """Retrieve the component ballot for this ballot.

        :returns: The component ballot for this ballot via the general ballot
            sub constituency.
        """
        return self.sc_general and self.sc_general.all() and\
            self.sc_general.all()[0].ballot_component

    @property
    def form_ballot_numbers(self):
        return Ballot.COMPONENT_TO_BALLOTS[self.number] if self.is_component\
            else [self.number]

    @property
    def is_component(self):
        return self.number in self.COMPONENT_TO_BALLOTS.keys()

    def __unicode__(self):
        return self.number


reversion.register(Ballot)
