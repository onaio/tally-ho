from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from libya_tally.apps.tally.models.office import Office
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.center_type import CenterType


class Center(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['code']

    sub_constituency = models.ForeignKey(SubConstituency,
                                         related_name='centers', null=True)

    center_type = enum.EnumField(CenterType)
    code = models.PositiveIntegerField(unique=True)  # a.k.a. Center Number
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    mahalla = models.TextField()
    name = models.TextField()
    office = models.ForeignKey(Office, null=True)
    region = models.TextField()
    village = models.TextField()

    def sc_code(self):
        return self.sub_constituency.code if self.sub_constituency else _(
            'Special')

    def __unicode__(self):
        return u'%s - %s' % (self.code, self.name)


reversion.register(Center)
