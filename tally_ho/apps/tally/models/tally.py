from django.db import models
from django_enumfield import enum

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.utils.templates import getTallyAdministerLink


class Tally(BaseModel):
    class Meta:
        app_label = 'tally'

    name = models.CharField(max_length=255, null=False, blank=False)
    active = models.BooleanField(default=True)
    disable_reason = enum.EnumField(DisableReason, null=True)

    def __unicode__(self):
        return u'%d - %s' % (self.id, self.name)

    @property
    def administer_button(self):
        return getTallyAdministerLink(self)
