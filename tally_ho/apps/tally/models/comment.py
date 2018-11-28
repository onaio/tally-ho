from django.db import models
import reversion

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.base_model import BaseModel


class Comment(BaseModel):
    class Meta:
        app_label = 'tally'

    text = models.TextField()
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


reversion.register(Comment)
