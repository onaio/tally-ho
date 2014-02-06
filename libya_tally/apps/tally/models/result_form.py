from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _
from django_enumfield import enum

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.center import Center
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.gender import Gender
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.utils.common import match_results


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
    rejected_count = models.PositiveIntegerField(default=0)
    serial_number = models.PositiveIntegerField(unique=True)
    station_number = models.PositiveSmallIntegerField(null=True)

    @property
    def general_results(self):
        return self.results.filter(
            active=True,
            candidate__race_type=RaceType.GENERAL)

    @property
    def women_results(self):
        return self.results.filter(
            active=True,
            candidate__race_type=RaceType.WOMEN)

    @property
    def has_general_results(self):
        return self.general_results.count() > 0

    @property
    def has_women_results(self):
        return self.women_results.count() > 0

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
        return Gender.to_name(self.gender)

    @property
    def corrections_required_text(self):
        return _(u"Corrections Required!")

    @property
    def general_match(self):
        return match_results(self, self.general_results) \
            if self.general_results else False

    @property
    def women_match(self):
        return match_results(self, self.women_results) \
            if self.women_results else True

    @property
    def reconciliationform(self):
        reconciliationforms = self.reconciliationform_set.filter(
            active=True, entry_version=EntryVersion.FINAL)

        if len(reconciliationforms) > 1:
            raise SuspiciousOperation(_(
                'Unexpected number of reconciliation forms'))
        elif len(reconciliationforms) == 0:
            return False

        return reconciliationforms[0]

    @property
    def reconciliationform_exists(self):
        return self.reconciliationform_set.filter(active=True).count()

    @property
    def reconciliation_match(self):
        results = self.reconciliationform_set.filter(active=True)
        if results and results.count() == 2:
            v1, v2 = [model_to_dict(result) for result in results]

            # remove keys that should differ
            del v1['id']
            del v1['entry_version']

            for k, v in v1.items():
                if v != v2[k]:
                    return False

            return True

        return False

    @property
    def corrections_passed(self):
        return (
            (not self.has_general_results or self.general_match) and
            (not self.reconciliationform_exists or
             self.reconciliation_match) and
            (not self.has_women_results or self.women_match))

    def reject(self):
        for result in self.results.all():
            result.active = False
            result.save()

        self.rejected_count = self.rejected_count + 1
        self.form_state = FormState.DATA_ENTRY_1
        self.save()
