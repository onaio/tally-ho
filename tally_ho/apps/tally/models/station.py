from datetime import timedelta

import reversion
from django.db import models
from django_enumfield import enum
from django.utils import timezone

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.dependencies import check_results_for_forms
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.utils.numbers import rounded_safe_div_percent
from tally_ho.libs.utils.templates import getActiveCenterLink
from tally_ho.libs.utils.templates import getActiveStationLink
from tally_ho.libs.models.enums.disable_reason import DisableReason


class Station(BaseModel):
    class Meta:
        app_label = 'tally'

    center = models.ForeignKey(Center, related_name='stations')
    sub_constituency = models.ForeignKey(
        SubConstituency, null=True, related_name='stations')

    gender = enum.EnumField(Gender)
    percent_archived = models.DecimalField(default=0, max_digits=5,
                                           decimal_places=2)
    percent_received = models.DecimalField(default=0, max_digits=5,
                                           decimal_places=2)
    registrants = models.PositiveIntegerField(null=True)
    station_number = models.PositiveSmallIntegerField()

    state_cache_hours = 1
    active = models.BooleanField(default=True)
    disable_reason = enum.EnumField(DisableReason, null=True)

    def __unicode__(self):
        return u'%s - %s' % (self.center.code, self.station_number)

    @property
    def center_code(self):
        return self.center.code if self.center else None

    @property
    def center_name(self):
        return self.center.name if self.center else None

    @property
    def center_active(self):
        return getActiveCenterLink(self) if self.center else None

    @property
    def station_active(self):
        return getActiveStationLink(self) if self else None

    @property
    def center_office(self):
        return self.center.office.name if self.center and self.center.office\
            else None

    @property
    def gender_name(self):
        return Gender.label(self.gender)

    @property
    def result_forms(self):
        return self.center.resultform_set.filter(
            station_number=self.station_number)

    @property
    def sub_constituency_code(self):
        return self.sub_constituency.code if self.sub_constituency else None

    def cache_archived_and_received(self):
        """Store the cached archived and received form percentages for this
        station.
        """
        all_forms = float(self.result_forms.count())
        archived = self.result_forms.filter(
            form_state=FormState.ARCHIVED).count()
        received = self.result_forms.exclude(
            form_state=FormState.UNSUBMITTED).count()

        self.percent_archived = rounded_safe_div_percent(archived, all_forms)
        self.percent_received = rounded_safe_div_percent(received, all_forms)
        self.save()

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

    @classmethod
    def update_cache(cls):
        """Check if this stations cache is out of date.
        """
        time_threshold = timezone.now() - timedelta(
            hours=cls.state_cache_hours)

        out_of_date = cls.objects.filter(modified_date__lt=time_threshold)

        for station in out_of_date:
            station.cache_archived_and_received()

reversion.register(Station)
