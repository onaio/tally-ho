from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.office import Office
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.gender import Gender
from libya_tally.libs.models.enums.race_type import RaceType

male_local = _('Male')
female_local = _('Female')

COMPONENT_TO_BALLOTS = {
    55: [26, 27, 28],
    56: [29, 30, 31],
    57: [34],
    58: [47],
}
MAX_BARCODE = 530000576


def model_field_to_dict(form):
    field_dict = model_to_dict(form)
    del field_dict['id']
    del field_dict['user']

    return field_dict


def get_matched_results(result_form, results):
    """
    Checks results entered by Data Entry 1 and Data Entry 2 clerks match.

    If we have more results from either data entry 1 or data entry 2,
    we reset to data entry 1 then raise a SuspiciousOperation exception.

    Returns a  list of matched results and unmatched results if any.
    """
    results_v1 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_1)\
        .values('candidate', 'votes')
    results_v2 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_2)\
        .values('candidate', 'votes')

    if results and (not results_v1 or not results_v2):
        raise Exception(_(u"Result Form has no double entries."))

    if results_v1.count() != results_v2.count():
        result_form.reject()
        raise SuspiciousOperation(_(
            u"Unexpected number of results in form %(barcode)s, "
            u"return result form to Data Entry 1." %
            {'barcode': result_form.barcode}))

    tuple_list = [i.items() for i in results_v1]
    matches = [rec for rec in results_v2 if rec.items() in tuple_list]
    no_match = [rec for rec in results_v2 if rec.items() not in tuple_list]

    return matches, no_match


def match_results(result_form, results=None):
    matches, no_match = get_matched_results(result_form, results)
    return len(no_match) == 0


def clean_reconciliation_forms(recon_queryset):
    if len(recon_queryset) > 1:
        field_dict = model_field_to_dict(recon_queryset[0])

        for form in recon_queryset[1:]:
            other_field_dict = model_field_to_dict(form)
            for k, v in other_field_dict.items():
                if field_dict[k] != v:
                    raise SuspiciousOperation(_(
                        'Unexpected number of reconciliation forms'))

            form.active = False
            form.save()

        return True

    return False


class ResultForm(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot = models.ForeignKey(Ballot, null=True)
    center = models.ForeignKey(Center, blank=True, null=True)
    user = models.ForeignKey(User, null=True)
    created_user = models.ForeignKey(User, null=True,
                                     related_name='created_user')

    audited_count = models.PositiveIntegerField(default=0)
    barcode = models.CharField(max_length=9, unique=True)
    date_seen = models.DateTimeField(null=True)
    form_stamped = models.NullBooleanField()
    form_state = enum.EnumField(FormState)
    gender = enum.EnumField(Gender, null=True)
    name = models.CharField(max_length=256, null=True)
    office = models.ForeignKey(Office, blank=True, null=True)
    rejected_count = models.PositiveIntegerField(default=0)
    serial_number = models.PositiveIntegerField(unique=True, null=True)
    skip_quarantine_checks = models.BooleanField(default=False)
    station_number = models.PositiveSmallIntegerField(blank=True, null=True)
    is_replacement = models.BooleanField(default=False)

    @property
    def results_final(self):
        return self.results.filter(
            active=True,
            entry_version=EntryVersion.FINAL)

    @property
    def station(self):
        if self.center:
            stations = self.center.stations.filter(
                station_number=self.station_number)
            if stations:
                return stations[0]

        return None

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
        return _(Gender.label(
            self.station.gender if self.station else self.gender))

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
    def corrections_reconciliationforms(self):
        reconciliationforms = self.reconciliationform_set.filter(active=True)

        de_1 = reconciliationforms.filter(
            entry_version=EntryVersion.DATA_ENTRY_1)
        de_2 = reconciliationforms.filter(
            entry_version=EntryVersion.DATA_ENTRY_2)

        if de_1.count() > 1:
            clean_reconciliation_forms(de_1)

        if de_2.count() > 1:
            clean_reconciliation_forms(de_2)

        return self.reconciliationform_set.filter(active=True)

    @property
    def reconciliationform(self):
        reconciliationforms = self.reconciliationform_set.filter(
            active=True, entry_version=EntryVersion.FINAL)

        if len(reconciliationforms) == 0:
            return False
        else:
            clean_reconciliation_forms(reconciliationforms)

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
    def clearance_team_reviewed_bool(self):
        return self.clearance and self.clearance.reviewed_team

    @property
    def clearance_team_reviewed(self):
        return self.clearance.user.username if self.clearance and\
            self.clearance.reviewed_team else _('No')

    @property
    def clearance_supervisor_reviewed(self):
        return self.clearance.supervisor and\
            self.clearance.supervisor.username if self.clearance and\
            self.clearance.reviewed_supervisor else _('No')

    @property
    def corrections_passed(self):
        return (
            (not self.has_general_results or self.general_match) and
            (not self.reconciliationform_exists or
             self.reconciliation_match) and
            (not self.has_women_results or self.women_match))

    def reject(self, new_state=FormState.DATA_ENTRY_1):
        for result in self.results.all():
            result.active = False
            result.save()

        for recon in self.reconciliationform_set.all():
            recon.active = False
            recon.save()

        self.rejected_count += 1
        self.form_state = new_state
        self.save()

    @property
    def center_code(self):
        return self.center.code if self.center else None

    @property
    def center_office(self):
        return self.center.office.name if self.center and self.center.office\
            else None

    @property
    def center_office_number(self):
        return self.center.office.number if self.center and self.center.office\
            else None

    @property
    def ballot_number(self):
        return self.ballot.number if self.ballot else None

    @property
    def ballot_race_type_name(self):
        if self.ballot:
            return self.ballot.race_type_name
        elif self.center and self.center.sub_constituency:
            return self.center.sub_constituency.form_type

        return _('Special')

    @property
    def has_recon(self):
        return self.center and self.center.code < 80001

    @property
    def sub_constituency_code(self):
        if self.center and self.center.sub_constituency:
            self.center.sub_constituency.code

    @property
    def center_name(self):
        return self.center.name if self.center else None

    @property
    def candidates(self):
        ballot = self.ballot
        candidates = list(ballot.candidates.order_by('race_type', 'order'))
        component_ballot = ballot.component_ballot

        if component_ballot:
            candidates += list(component_ballot.candidates.order_by('order'))

        return candidates

    @classmethod
    def distinct_filter(self, qs):
        return qs.filter(
            center__isnull=False,
            station_number__isnull=False,
            ballot__isnull=False).extra(
            where=["barcode::integer <= %s"],
            params=[MAX_BARCODE]).order_by(
            'center__id', 'station_number', 'ballot__id',
            'form_state').distinct(
            'center__id', 'station_number', 'ballot__id')

    @classmethod
    def distinct_for_component(cls, ballot):
        return cls.distinct_filter(cls.objects.filter(
            ballot__number__in=COMPONENT_TO_BALLOTS[ballot.number]))

    @classmethod
    def distinct_forms(cls):
        return cls.distinct_filter(cls.objects)

    @classmethod
    def distinct_form_pks(cls):
        # Calling '.values(id)' here does not preserve the distinct order by,
        # this leads to not choosing the archived replacement form.
        # TODO use a subquery that preserves the distinct and the order by
        # or cache this.
        return [r.pk for r in cls.distinct_filter(cls.distinct_forms())]

    @classmethod
    def forms_in_state(cls, state):
        pks = cls.distinct_form_pks()

        return cls.objects.filter(id__in=pks, form_state=state)

    @classmethod
    def generate_barcode(cls):
        result_forms = cls.objects.all().order_by('-barcode')
        highest_barcode = result_forms[0].barcode if result_forms else\
            10000000
        return int(highest_barcode) + 1

    def send_to_clearance(self):
        self.form_state = FormState.CLEARANCE
        self.save()

    @classmethod
    def unsubmitted_result_forms(self):
        not_in_states = [FormState.ARCHIVED, FormState.ARCHIVING,
                         FormState.AUDIT, FormState.CLEARANCE,
                         FormState.CORRECTION, FormState.DATA_ENTRY_1,
                         FormState.DATA_ENTRY_2, FormState.INTAKE,
                         FormState.QUALITY_CONTROL]
        return ResultForm.objects.exclude(
            Q(form_state__in=not_in_states) | Q(center__isnull=True))


reversion.register(ResultForm)
