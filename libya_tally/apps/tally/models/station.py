import reversion

from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_enumfield import enum

from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.gender import Gender


class Station(BaseModel):
    class Meta:
        app_label = 'tally'

    center = models.ForeignKey(Center, related_name='stations')
    sub_constituency = models.ForeignKey(
        SubConstituency, null=True, related_name='stations')

    gender = enum.EnumField(Gender)
    registrants = models.PositiveIntegerField(null=True)
    station_number = models.PositiveSmallIntegerField()

    def __unicode__(self):
        return u'%s - %s' % (self.center.code, self.station_number)

    @property
    def gender_name(self):
        return Gender.label(self.gender)

    @property
    def center_code(self):
        return self.center.code if self.center else None

    @property
    def center_office(self):
        return self.center.office.name if self.center and self.center.office\
            else None

    @property
    def sub_constituency_code(self):
        return self.sub_constituency.code if self.sub_constituency else None

    @property
    def center_name(self):
        return self.center.name if self.center else None

    def remove(self):
        """Remove station and result forms for the station,
        only if we have no results for the station.
        """
        resultforms = self.center.resultform_set.filter(
            station_number=self.station_number)
        for resultform in resultforms:
            if resultform.results.count():
                raise Exception(_(u"Results exist for %(barcode)s" %
                                  {'barcode': resultform.barcode}))
        resultforms.delete()
        self.delete()

reversion.register(Station)
