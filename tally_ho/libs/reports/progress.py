from django.db.models.query import QuerySet
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState


def rounded_percent(numerator, denominator):
    return round(100 * numerator / float(denominator), 2)


class ProgressReport(object):

    def __init__(self, tally_id):
        self.tally_id = tally_id
        self.filtered_queryset = self.queryset = ResultForm.distinct_forms(tally_id)

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

        self.filtered_queryset = self.get_filtered_queryset().filter(
            ballot__number__in=ballot.form_ballot_numbers, tally__id=self.tally)
        self.queryset = self.get_queryset().filter(
            ballot__number__in=ballot.form_ballot_numbers, tally__id=self.tally)

        return self

    def for_center_office(self, office):

        filtered_queryset = self.get_filtered_queryset().filter(center__office=office)
        queryset = self.get_queryset().filter(center__office=office)

        return filtered_queryset.count()


class ExpectedProgressReport(ProgressReport):
    label = _(u"Expected")

    def __init__(self, tally_id):
        super(ExpectedProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.distinct_forms(self.tally_id)


class IntakenProgressReport(ProgressReport):
    label = _(u"Intaken")

    def __init__(self, tally_id):
        super(IntakenProgressReport, self).__init__(tally_id)

        pks = ResultForm.distinct_form_pks(self.tally_id)

        self.filtered_queryset = ResultForm.objects.filter(
            id__in=pks).exclude(form_state=FormState.UNSUBMITTED)


class ArchivedProgressReport(ProgressReport):
    label = _(u"Archived")

    def __init__(self, tally_id):
        super(ArchivedProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.ARCHIVED, tally_id=self.tally_id)


class IntakeProgressReport(ProgressReport):
    label = _(u"Intake")

    def __init__(self, tally_id):
        super(IntakeProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.INTAKE, tally_id=self.tally_id)


class ClearanceProgressReport(ProgressReport):
    label = _(u"Clearance")

    def __init__(self, tally_id):
        super(ClearanceProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.CLEARANCE, tally_id=self.tally_id)


class DataEntry1ProgressReport(ProgressReport):
    label = _(u"Data Entry 1")

    def __init__(self, tally_id):
        super(DataEntry1ProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.DATA_ENTRY_1, tally_id=self.tally_id)


class DataEntry2ProgressReport(ProgressReport):
    label = _(u"Data Entry 2")

    def __init__(self, tally_id):
        super(DataEntry2ProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.DATA_ENTRY_2, tally_id=self.tally_id)


class CorrectionProgressReport(ProgressReport):
    label = _(u"Correction")

    def __init__(self, tally_id):
        super(CorrectionProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.CORRECTION, tally_id=self.tally_id)


class QualityControlProgressReport(ProgressReport):
    label = _(u"Quality Control")

    def __init__(self, tally_id):
        super(QualityControlProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.QUALITY_CONTROL, tally_id=self.tally_id)


class ArchivingProgressReport(ProgressReport):
    label = _(u"Archiving")

    def __init__(self, tally_id):
        super(ArchivingProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.ARCHIVING, tally_id=self.tally_id)


class AuditProgressReport(ProgressReport):
    label = _(u"Audit")

    def __init__(self, tally_id):
        super(AuditProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.AUDIT, tally_id=self.tally_id)


class NotRecievedProgressReport(ProgressReport):
    label = _(u"Not Received")

    def __init__(self, tally_id):
        super(NotRecievedProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(FormState.UNSUBMITTED, tally_id=self.tally_id)
