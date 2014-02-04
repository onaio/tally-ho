from django.contrib.auth.models import User
from django.db import models
from django_enumfield import enum

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.center import Center
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.gender import Gender
from libya_tally.libs.models.enums.race_type import RaceType


class ResultForm(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot = models.ForeignKey(Ballot)
    center = models.ForeignKey(Center, null=True)
    user = models.ForeignKey(User, null=True)

    barcode = models.PositiveIntegerField(unique=True)
    form_stamped = models.NullBooleanField()
    form_state = enum.EnumField(FormState)
    gender = enum.EnumField(Gender, null=True)
    name = models.CharField(max_length=256, null=True)
    office = models.CharField(max_length=256, null=True)
    serial_number = models.PositiveIntegerField(unique=True)
    station_number = models.PositiveSmallIntegerField(null=True)

    @property
    def has_general_results(self):
        return self.results.filter(
            candidate__race_type=RaceType.GENERAL).count() > 0

    @property
    def has_women_results(self):
        return self.results.filter(
            candidate__race_type=RaceType.WOMEN).count() > 0

    @property
    def qualitycontrol(self):
        quality_controls = self.qualitycontrol_set.filter(active=True)
        return quality_controls[0] if len(quality_controls) else None

    @property
    def audit(self):
        audits = self.audit_set.filter(active=True)
        return audits[0] if len(audits) else None

    @property
    def form_state_name(self):
        return FormState.to_name(self.form_state)

    @property
    def gender_name(self):
        return dict(Gender.choices())[self.gender]
