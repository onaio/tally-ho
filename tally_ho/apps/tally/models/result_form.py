from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.db.models import Q, Sum
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.clearance_resolution import ClearanceResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.utils.templates import get_result_form_edit_delete_links

male_local = _('Male')
female_local = _('Female')


def model_field_to_dict(form):
    field_dict = model_to_dict(form)
    del field_dict['id']
    del field_dict['user']

    return field_dict


def get_matched_results(result_form, results):
    """Checks results entered by Data Entry 1 and Data Entry 2 clerks match.

    If we have more results from either data entry 1 or data entry 2,
    we reset to data entry 1 then raise a SuspiciousOperation exception.

    :param result_form: The result form to find matching results for.
    :param results: The results to look within when finding matching results.

    :returns: A list of matched and unmatched results.
    """
    results_v1 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_1)\
        .values('candidate', 'votes')
    results_v2 = results.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_2)\
        .values('candidate', 'votes')

    if results and (not results_v1 or not results_v2):
        raise SuspiciousOperation(_(u"Result Form has no double entries."))

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
    """True is all results match, otherwise false.

    :param result_form: The result form to find match results for.
    :param results: The results to filter when finding matched results.
    """
    _, no_match = get_matched_results(result_form, results)
    return len(no_match) == 0


def sanity_check_final_results(result_form):
    """Deactivate duplicate final results.

    Each result form should have one final result for each candidate.  If there
    are multiple final results for a candidate deactivate them.

    :param result_form: The result form to check final results for.

    :raises: `SuspiciousOperation` if the votes in the final results for the
        same candidate and result form do not match.
    """
    for candidate in result_form.candidates:
        results = result_form.results_final.filter(candidate=candidate)
        other_result = results[0]

        if results.count() > 1:
            for result in results[1:]:

                if result.votes != other_result.votes:
                    raise SuspiciousOperation(_("Votes do not match!"))

                result.active = False
                result.save()


def clean_reconciliation_forms(recon_queryset):
    """Deactivate duplicate reconciliation forms for the same form state.

    Check that all reconciliation forms in the same state match and deactivate
    all but one if there are more than one.

    :param recon_queryset: A reconciliaton form queryset to clean results for.

    :raises: `SuspiciousOperation` if the recon forms do not have the exact
        same results.

    :returns: True if any forms need to be cleaned, False otherwise.
    """
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
        indexes = [
            models.Index(fields=['center',
                                 'station_number',
                                 'ballot',
                                 'tally']),
        ]
        unique_together = (('barcode', 'tally'), ('serial_number', 'tally'))

    START_BARCODE = 10000000
    OCV_CENTER_MIN = 80001

    ballot = models.ForeignKey(Ballot, null=True, on_delete=models.PROTECT)
    center = models.ForeignKey(Center, blank=True, null=True,
                               on_delete=models.PROTECT)
    user = models.ForeignKey(UserProfile, null=True, on_delete=models.PROTECT)
    created_user = models.ForeignKey(UserProfile, null=True,
                                     on_delete=models.PROTECT,
                                     related_name='created_user')

    audited_count = models.PositiveIntegerField(default=0)
    barcode = models.CharField(max_length=255)
    date_seen = models.DateTimeField(null=True)
    duplicate_reviewed = models.BooleanField(default=False)
    form_stamped = models.BooleanField(null=True)
    form_state = EnumIntegerField(FormState)
    previous_form_state = EnumIntegerField(FormState, blank=True, null=True)
    gender = EnumIntegerField(Gender, null=True)
    name = models.CharField(max_length=256, null=True)
    office = models.ForeignKey(Office, blank=True, null=True,
                               on_delete=models.PROTECT)
    rejected_count = models.PositiveIntegerField(default=0)
    reject_reason = models.TextField(null=True, blank=True)
    serial_number = models.PositiveIntegerField(null=True)
    skip_quarantine_checks = models.BooleanField(default=False)
    station_number = models.PositiveSmallIntegerField(blank=True, null=True)
    is_replacement = models.BooleanField(default=False)
    intake_printed = models.BooleanField(default=False)
    clearance_printed = models.BooleanField(default=False)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='result_forms',
                              on_delete=models.PROTECT)

    # Field used in result duplicated list view
    results_duplicated = []

    @property
    def results_final(self):
        """Return the final active results for this result form."""
        return self.results.filter(active=True,
                                   entry_version=EntryVersion.FINAL)

    @property
    def station(self):
        """Return the station for this result form.

        Stations are indirectly tied to result forms through the station
        number and the centers linked to the result form.  Find the station for
        this result form by finding that with a matching station number in the
        center tied to this result form.
        """
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
    def presidential_results(self):
        return self.results.filter(
            active=True,
            candidate__race_type=RaceType.PRESIDENTIAL)

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
    def has_presidential_results(self):
        return self.presidential_results.count() > 0

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
    def audit_recommendation(self):
        if self.audit:
            recomendation_index = self.audit.resolution_recommendation
            return ClearanceResolution.choices()[recomendation_index.value][1]

    @property
    def audit_quaritine_checks(self):
        if self.audit:
            return self.audit.quarantine_checks.all().values('name')

    @property
    def form_state_name(self):
        return self.form_state.label

    @property
    def gender_name(self):
        return _(self.station.gender.name if self.station
                 else self.gender.name)

    @property
    def num_votes(self):
        return list(
            self.results_final.aggregate(Sum('votes')).values())[0] or 0

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
    def presidential_match(self):
        return match_results(self, self.presidential_results) \
            if self.presidential_results else False

    @property
    def corrections_reconciliationforms(self):
        """Return the reconciliation forms for this result form to be used in
        corrections.

        If there are extract Data Entry 1 or 2 reconciliation forms, clean
        those forms.

        :returns: The reconciliation forms for this result form after cleaning
            Data Entry 1 and 2 conciliation forms.
        """
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
        """Return the final reconciliation form for this result form.

        Clean the final reconciliation forms if there are more than one.

        :returns: The final reconciliation form for this result form.
        """
        final = self.reconciliationform_set.filter(
            active=True, entry_version=EntryVersion.FINAL)

        if len(final) == 0:
            return False

        final.count() > 1 and clean_reconciliation_forms(final)

        return final[0]

    @property
    def reconciliationform_exists(self):
        return self.reconciliationform_set.filter(active=True).count()

    @property
    def reconciliation_match(self):
        """Return True if there are two reconciliation forms and they match,
        otherwise return False.

        :returns: True if there are two reonciliation forms and they match,
            False otherwise.
        """
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
    def clearance_recommendation(self):
        if self.clearance:
            recomendation_index = self.clearance.resolution_recommendation
            return ClearanceResolution.choices()[recomendation_index.value][1]

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
        """If for all types of results for this result form the entries in
        Data Entry 1 and 2 match return True, otherwise False.

        :returns: True if the results from Data Entry 1 and 2 match, otherwise
            returns False.
        """
        return (
            (not self.has_presidential_results or self.presidential_match) and
            (not self.has_general_results or self.general_match) and
            (not self.reconciliationform_exists or
             self.reconciliation_match) and
            (not self.has_women_results or self.women_match))

    def reject(self, new_state=FormState.DATA_ENTRY_1, reject_reason=None):
        """Deactivate existing results and reconciliation forms for this result
        form, change the state, and increment the rejected count.

        :param new_state: The state to set the form to.
        """
        for result in self.results.all():
            result.active = False
            result.save()

        for recon in self.reconciliationform_set.all():
            recon.active = False
            recon.save()

        self.rejected_count += 1
        self.form_state = new_state
        self.duplicate_reviewed = False
        self.reject_reason = reject_reason
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
        """Any forms with assigned centers that are below the Out-of-country
        Voting minimum center number will have reconciliation forms.
        """
        return self.center and self.center.code < self.OCV_CENTER_MIN

    @property
    def sub_constituency_code(self):
        if self.center and self.center.sub_constituency:
            return self.center.sub_constituency.code

    @property
    def center_name(self):
        return self.center.name if self.center else None

    @property
    def candidates(self):
        """Get the candidates for this result form ordered by ballot order.

        :returns: A list of candidates that appear on this result form.
        """
        return list(self.ballot.candidates.order_by('order'))

    @property
    def get_action_button(self):
        return get_result_form_edit_delete_links(self) if self else None

    @classmethod
    def distinct_filter(self, qs, tally_id=None):
        """Add a distinct filter onto a queryset.

        Return a queryset that accounts for duplicate replacement forms, orders
        the results to take the duplicate which is archived if one exists, and
        removes the barcodes that are not in the original dataset.

        :param qs: The queryset to filer.

        :returns: A distinct, ordered, and filtered queryset.
        """
        new_qs = qs.filter(
            center__isnull=False,
            station_number__isnull=False,
            ballot__isnull=False).order_by(
            'center__id', 'station_number', 'ballot__id',
            'form_state').distinct(
            'center__id', 'station_number', 'ballot__id')

        return new_qs.filter(tally__id=tally_id) if tally_id else new_qs

    @classmethod
    def distinct_for_component(cls, ballot, tally_id=None):
        """Return the distinct result forms for this ballot, taking into
        account the possiblity of a component ballot.

        :param ballot: The ballot to return forms for.

        :returns: A distinct list of result forms.
        """
        return cls.distinct_filter(cls.objects.filter(
            ballot__number__in=ballot.form_ballot_numbers,
            tally__id=tally_id))

    @classmethod
    def distinct_forms(cls, tally_id=None):
        if tally_id:
            return cls.distinct_filter(cls.objects, tally_id)

        return cls.distinct_filter(cls.objects)

    @classmethod
    def distinct_form_pks(cls, tally_id=None):
        return cls.distinct_filter(cls.distinct_forms(tally_id),
                                   tally_id).values_list('id', flat=True)

    @classmethod
    def forms_in_state(cls, state, pks=None, tally_id=None):
        if not pks:
            pks = cls.distinct_form_pks(tally_id)

        qs = cls.objects.filter(id__in=pks, form_state=state)

        return qs.filter(tally__id=tally_id) if tally_id else qs

    @classmethod
    def generate_barcode(cls, tally_id=None):
        """Create a new barcode.

        Create a new barcode that is not already in the system by taking the
        greatest barcode in the system and incrementing it by one.

        Note this does not account for multiple request or threads.

        :returns: A new unique integer barcode.
        """
        result_forms = cls.objects.filter(
            tally__id=tally_id).order_by('-barcode')
        highest_barcode = result_forms[0].barcode if result_forms else\
            cls.START_BARCODE

        return int(highest_barcode) + 1

    def get_duplicated_forms(self, center=None, station_number=None):
        """Get all the result forms for this center and station_number.

        :param center: Check result forms from this center.
        :param station_number: Check result forms with this station number.

        :returns: Array with the forms for this center, station, ballot,
                  and considering form state.
        """
        if not center:
            center = self.center

        if not station_number:
            station_number = self.station_number

        qs = ResultForm.objects.filter(tally=self.tally)
        qs = qs.filter(
            Q(center=center), Q(center__isnull=False),
            Q(station_number=station_number), Q(station_number__isnull=False),
            Q(ballot=self.ballot), Q(ballot__isnull=False))

        if self.form_state in [FormState.UNSUBMITTED, FormState.CLEARANCE]:
            qs = qs.exclude(Q(form_state=FormState.UNSUBMITTED))
        elif self.form_state == FormState.INTAKE:
            qs = qs.exclude(Q(form_state=FormState.UNSUBMITTED)
                            | Q(form_state=FormState.INTAKE))
        else:
            return []

        return qs.order_by('created_date')

    def send_to_clearance(self):
        self.previous_form_state = self.form_state
        self.form_state = FormState.CLEARANCE

        if self.audit and self.audit.active:
            audit = self.audit
            audit.active = False
            audit.save()
        self.save()


reversion.register(ResultForm)
