from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
import reversion

from tally_ho.libs.models.base_model import BaseModel


class QuarantineCheck(BaseModel):
    class Meta:
        app_label = 'tally'

    user = models.ForeignKey(User, null=True)

    name = models.CharField(max_length=256, unique=True)
    method = models.CharField(max_length=256, unique=True)
    value = models.FloatField()
    percentage = models.FloatField(default=100)

    def local_name(self):
        return _(self.name)


reversion.register(QuarantineCheck)
