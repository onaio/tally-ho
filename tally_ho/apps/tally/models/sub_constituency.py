from django.db import models
import reversion

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.libs.models.base_model import BaseModel


class SubConstituency(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot_component = models.ForeignKey(Ballot, null=True,
                                         on_delete=models.PROTECT,
                                         related_name='sc_component')
    ballot_presidential = models.ForeignKey(Ballot, null=True,
                                            on_delete=models.PROTECT,
                                            related_name='sc_presidential')
    ballot_general = models.ForeignKey(Ballot, null=True,
                                       on_delete=models.PROTECT,
                                       related_name='sc_general')
    ballot_women = models.ForeignKey(Ballot, null=True,
                                     on_delete=models.PROTECT,
                                     related_name='sc_women')
    ballots = models.ManyToManyField(Ballot,
                                     blank=True,
                                     related_name='sc_ballots')
    code = models.PositiveSmallIntegerField()  # aka SubCon number
    field_office = models.CharField(max_length=256, null=True)
    number_of_ballots = models.PositiveSmallIntegerField(null=True)
    races = models.PositiveSmallIntegerField(null=True)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='tally',
                              on_delete=models.PROTECT)
    constituency = models.ForeignKey(Constituency,
                                     null=True,
                                     blank=True,
                                     related_name='constituency',
                                     on_delete=models.PROTECT)

    def __str__(self):
        return u'%s - %s' % (self.code, self.tally.name)

    def get_ballots(self):
        """Return the ballots used in this subconstituency.

        :returns: The ballots used in this subconstituency.
        """
        if self.ballots:
            return self.ballots.all()
        else:
            return None


reversion.register(SubConstituency)
