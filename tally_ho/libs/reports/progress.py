from django.db.models.query import QuerySet
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState


def rounded_percent(numerator, denominator):
    return round(100 * numerator / float(denominator), 2)


class ProgressReport(object):
    queryset = ResultForm.distinct_forms()

    def get_queryset(self):
        if self.queryset is None or not isinstance(self.queryset, QuerySet):
            raise ImproperlyConfigured(
                u"queryset needs to be of instance QuerySet")

        return self.queryset

    def get_filtered_queryset(self):
        if not isinstance(self.filtered_queryset, QuerySet):
            raise ImproperlyConfigured(
                u"queryset needs to be of instance QuerySet")

        return self.filtered_queryset

    def numerator(self):
        return self.get_filtered_queryset().count()

    number = property(numerator)

    def denominator(self):
        return self.queryset.count()

    total = property(denominator)

    def percentage_value(self):
        if self.denominator() <= 0:
            return _(u"No results")

        return rounded_percent(self.numerator(), self.denominator())

    percentage = property(percentage_value)

    def for_ballot(self, ballot):
        obj = self.__class__()

        obj.filtered_queryset = self.get_filtered_queryset().filter(
            ballot__number__in=ballot.form_ballot_numbers)
        obj.queryset = self.get_queryset().filter(
            ballot__number__in=ballot.form_ballot_numbers)

        return obj

    def for_center_office(self, office):
        obj = self.__class__()
        obj.filtered_queryset = \
            self.get_filtered_queryset().filter(center__office=office)
        obj.queryset = self.get_queryset().filter(center__office=office)

        return obj


class ExpectedProgressReport(ProgressReport):
    filtered_queryset = ResultForm.distinct_forms()
    label = _(u"Expected")


class IntakenProgressReport(ProgressReport):
    pks = ResultForm.distinct_form_pks()

    filtered_queryset = ResultForm.objects.filter(
        id__in=pks).exclude(form_state=FormState.UNSUBMITTED)
    label = _(u"Intaken")


class ArchivedProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.ARCHIVED)
    label = _(u"Archived")


class IntakeProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.INTAKE)
    label = _(u"Intake")


class ClearanceProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.CLEARANCE)
    label = _(u"Clearance")

class ClearancePendingsProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.CLEARANCE_PENDING_STATE)
    label = _(u"Clearance Pendings")

class DataEntry1ProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.DATA_ENTRY_1)
    label = _(u"Data Entry 1")


class DataEntry2ProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.DATA_ENTRY_2)
    label = _(u"Data Entry 2")


class CorrectionProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.CORRECTION)
    label = _(u"Correction")


class QualityControlProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.QUALITY_CONTROL)
    label = _(u"Quality Control")


class ArchivingProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.ARCHIVING)
    label = _(u"Archiving")


class AuditProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.AUDIT)
    label = _(u"Audit")

class AuditPendingsProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.AUDIT_PENDING_STATE)
    label = _(u"Audit Pendings")


class NotRecievedProgressReport(ProgressReport):
    filtered_queryset = ResultForm.forms_in_state(FormState.UNSUBMITTED)
    label = _(u"Not Received")
