from django.db import models
from django_enumfield import enum

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.disable_reason import DisableReason


class Tally(BaseModel):
    class Meta:
        app_label = 'tally'

    name = models.CharField(max_length=255, null=False, blank=False)
    active = models.BooleanField(default=True)
    election_date = models.DateField(null=False, blank=False)
    disable_reason = enum.EnumField(DisableReason, null=True)
