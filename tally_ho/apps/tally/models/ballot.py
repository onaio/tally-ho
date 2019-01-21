from django.db import models
from django.utils.translation import ugettext as _
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.models.enums.disable_reason import DisableReason


COMPONENT_TO_BALLOTS = {
    55: [26, 27, 28],
    56: [29, 30, 31],
    57: [34],
    58: [47],
}


def is_component(number):
    return number in COMPONENT_TO_BALLOTS.keys()


def form_ballot_numbers(number):
    return COMPONENT_TO_BALLOTS[number] if is_component(number) else [number]


def sub_constituency(sc_general, sc_women, sc_component):
    return sc_general or sc_women or sc_component


def race_type_name(race_type, sc_general):
        if sc_general and sc_general.ballot_component:
            return _('General and Component')

        return race_type.name


class Ballot(BaseModel):
    class Meta:
        app_label = 'tally'
        indexes = [
            models.Index(fields=['number']),
        ]
        ordering = ['number']
        unique_together = ('number', 'tally')

    active = models.BooleanField(default=True)
    available_for_release = models.BooleanField(default=False)
    disable_reason = EnumIntegerField(DisableReason, null=True, default=None)
    document = models.FileField(null=True, blank=True)
    number = models.PositiveSmallIntegerField()
    race_type = EnumIntegerField(RaceType)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='ballots',
                              on_delete=models.PROTECT)

    @property
    def race_type_name(self):
        return race_type_name(self.race_type, self.sc_general.first())

    @property
    def sub_constituency(self):
        return sub_constituency(self.sc_general.first(),
                                self.sc_women.first(),
                                self.sc_component.first())

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
        return form_ballot_numbers(self.number)

    @property
    def is_component(self):
        return is_component(self.number)

    def __str__(self):
        return u'%s - %s' % (self.number, self.race_type_name)


reversion.register(Ballot)
