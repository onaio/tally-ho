import reversion

from django.db import models

from django_enumfield import enum

from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.dependencies import check_results_for_forms
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
        """Remove this station and result forms for this station.

        Do not perform any action if have results for any result form
        associated with this station.

        :raises: `Exception` if any results exists for this station.
        """
        resultforms = self.center.resultform_set.filter(
            station_number=self.station_number)

        check_results_for_forms(resultforms)
        resultforms.delete()
        self.delete()

reversion.register(Station)
