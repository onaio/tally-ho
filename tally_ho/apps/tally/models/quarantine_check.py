from django.db import models
from django.utils.translation import ugettext as _
import reversion

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.apps.tally.models.user_profile import UserProfile


class QuarantineCheck(BaseModel):
    class Meta:
        app_label = 'tally'

    user = models.ForeignKey(UserProfile, null=True, on_delete=models.PROTECT)

    name = models.CharField(max_length=256, unique=True)
    method = models.CharField(max_length=256, unique=True)
    value = models.FloatField()
    percentage = models.FloatField(default=100)
    active = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)

    def local_name(self):
        return _(self.name)


reversion.register(QuarantineCheck)
