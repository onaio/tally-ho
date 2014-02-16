from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.center import Center
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.gender import Gender
from libya_tally.libs.models.enums.race_type import RaceType


def get_matched_results(result_form, results):
    results_v1 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_1)\
        .values('candidate', 'votes')
    results_v2 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_2)\
        .values('candidate', 'votes')

    if results and (not results_v1 or not results_v2):
        raise Exception(_(u"Result Form has no double entries."))

    if results_v1.count() != results_v2.count():
        return False

    tuple_list = [i.items() for i in results_v1]
    matches = [rec for rec in results_v2 if rec.items() in tuple_list]
    no_match = [rec for rec in results_v2 if rec.items() not in tuple_list]

    return matches, no_match


def match_results(result_form, results=None):
    matches, no_match = get_matched_results(result_form, results)
    return len(no_match) == 0


class ResultForm(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot = models.ForeignKey(Ballot, null=True)
    center = models.ForeignKey(Center, blank=True, null=True)
    user = models.ForeignKey(User, null=True)
    created_user = models.ForeignKey(User, null=True,
                                     related_name='created_user')

    barcode = models.PositiveIntegerField(unique=True)
    date_seen = models.DateTimeField(null=True)
    form_stamped = models.NullBooleanField()
    form_state = enum.EnumField(FormState)
    gender = enum.EnumField(Gender, null=True)
    name = models.CharField(max_length=256, null=True)
    office = models.CharField(max_length=256, blank=True, null=True)
    rejected_count = models.PositiveIntegerField(default=0)
    serial_number = models.PositiveIntegerField(unique=True, null=True)
    skip_quarantine_checks = models.BooleanField(default=False)
    station_number = models.PositiveSmallIntegerField(blank=True, null=True)

    @property
    def barcode_padded(self):
        barcode = str(self.barcode)
        return barcode if len(barcode) == 9 else '0%s' % barcode

    @property
    def results_final(self):
        return self.results.filter(
            active=True,
            entry_version=EntryVersion.FINAL)

    @property
    def station(self):
        return self.center.stations.filter(gender=self.gender)[0]

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
    def audit_team_reviewed(self):
        return self.audit.user.username if self.audit and\
            self.audit.reviewed_team else _('No')

    @property
    def audit_supervisor_reviewed(self):
        return self.audit.supervisor.username if self.audit and\
            self.audit.reviewed_supervisor else _('No')

    @property
    def form_state_name(self):
        return FormState.label(self.form_state)

    @property
    def gender_name(self):
        return Gender.label(self.gender)

    @property
    def num_votes(self):
        return sum([r.votes for r in self.results_final])

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
    def clearance(self):
        clearance = self.clearances.filter(active=True)
        return clearance[0] if clearance else None

    @property
    def clearance_team_reviewed(self):
        return _('Yes') if self.clearance and self.clearance.reviewed_team\
            else _('No')

    @property
    def clearance_supervisor_reviewed(self):
        return _('Yes') if self.clearance and\
            self.clearance.reviewed_supervisor else _('No')

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

        for recon in self.reconciliationform_set.all():
            recon.active = False
            recon.save()

        self.rejected_count = self.rejected_count + 1
        self.form_state = FormState.DATA_ENTRY_1
        self.save()

    @property
    def center_code(self):
        return self.center.code if self.center else None

    @property
    def center_office(self):
        return self.center.office if self.center else None

    @property
    def ballot_number(self):
        return self.ballot.number if self.ballot else None

    @property
    def ballot_race_type_name(self):
        return self.ballot.race_type_name if self.ballot else None

    @property
    def sub_constituency_code(self):
        return self.sub_constituency.code if self.sub_constituency else None

    @property
    def center_name(self):
        return self.center.name if self.center else None

    @classmethod
    def generate_barcode(cls):
        result_forms = cls.objects.all().order_by('-barcode')
        highest_barcode = result_forms[0].barcode if result_forms else\
            10000000
        return highest_barcode + 1


reversion.register(ResultForm)
