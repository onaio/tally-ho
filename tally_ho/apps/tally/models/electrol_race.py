from django.db import models
import reversion

from tally_ho.libs.models.base_model import BaseModel


class ElectrolRace(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['ballot_name']
        unique_together = (('election_level', 'ballot_name'))
    election_level = models.CharField(max_length=256, null=True)
    ballot_name = models.CharField(max_length=256, null=True)

    def __str__(self):
        return u'%s - %s' % (self.election_level, self.ballot_name)


reversion.register(ElectrolRace)
