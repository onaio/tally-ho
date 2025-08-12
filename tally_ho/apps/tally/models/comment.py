import reversion
from django.db import models

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.base_model import BaseModel


class Comment(BaseModel):
    class Meta:
        app_label = 'tally'
        indexes = [
            models.Index(fields=['ballot', 'tally']),
            models.Index(fields=['center', 'tally']),
            models.Index(fields=['station', 'tally']),
            models.Index(fields=['electrol_race', 'tally']),
        ]

    text = models.TextField()
    electrol_race = models.ForeignKey(ElectrolRace,
                                      on_delete=models.PROTECT,
                                      related_name='comments',
                                      null=True)
    ballot = models.ForeignKey(Ballot,
                               on_delete=models.PROTECT,
                               related_name='comments',
                               null=True)
    center = models.ForeignKey(Center,
                               on_delete=models.PROTECT,
                               related_name='comments',
                               null=True)
    station = models.ForeignKey(Station,
                                on_delete=models.PROTECT,
                                related_name='comments',
                                null=True)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='comments',
                              on_delete=models.PROTECT)


reversion.register(Comment)
