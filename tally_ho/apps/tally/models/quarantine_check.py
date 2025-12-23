from django.db import models
from django.utils.translation import gettext_lazy as _
import reversion

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.apps.tally.models.user_profile import UserProfile


class QuarantineCheck(BaseModel):
    class Meta:
        app_label = 'tally'
        unique_together = [['method', 'tally'], ['name', 'tally']]

    user = models.ForeignKey(UserProfile, null=True, on_delete=models.PROTECT)
    tally = models.ForeignKey(
        'Tally',
        on_delete=models.PROTECT,
        related_name='quarantine_checks'
    )

    name = models.CharField(max_length=256)
    method = models.CharField(max_length=256)
    value = models.IntegerField(default=0)
    percentage = models.IntegerField(default=0)
    active = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)

    def local_name(self):
        return _(self.name)


reversion.register(QuarantineCheck)
