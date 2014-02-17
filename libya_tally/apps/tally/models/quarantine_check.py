from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
import reversion

from libya_tally.libs.models.base_model import BaseModel


class QuarantineCheck(BaseModel):
    class Meta:
        app_label = 'tally'

    user = models.ForeignKey(User, null=True)

    name = models.CharField(max_length=256, unique=True)
    method = models.CharField(max_length=256, unique=True)
    value = models.FloatField()

    def local_name(self):
        return {
            'Trigger 1 - Guard against overvoting':
            _('Trigger 1 - Guard against overvoting'),
            'Trigger 2 - Guard against errors and tampering with the form':
            _('Trigger 2 - Guard against errors and tampering with the form')
        }.get(self.name, self.name)


reversion.register(QuarantineCheck)
