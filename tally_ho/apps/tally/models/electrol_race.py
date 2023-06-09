import reversion
from django.db import models
from enumfields import EnumIntegerField

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.utils.templates import get_electrol_race_link
from tally_ho.apps.tally.models.tally import Tally


class ElectrolRace(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['ballot_name']
        unique_together = (('election_level', 'ballot_name', 'tally'))
    election_level = models.CharField(max_length=256, null=True)
    ballot_name = models.CharField(max_length=256, null=True)
    active = models.BooleanField(default=True)
    disable_reason = EnumIntegerField(DisableReason, null=True, default=None)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='electrol_races',
                              on_delete=models.PROTECT)

    def __str__(self):
        return u'%s - %s' % (self.election_level, self.ballot_name)

    @property
    def get_action_button(self):
        return get_electrol_race_link(self) if self else None


reversion.register(ElectrolRace)
