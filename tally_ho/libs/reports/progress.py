from django.contrib.postgres.aggregates import ArrayAgg

from django.db.models import Sum, When, Case, Value as V
from django.db.models.query import QuerySet
from django.db.models.functions import Coalesce
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState


def rounded_percent(numerator, denominator):
    return round(100 * numerator / float(denominator), 2) if\
        denominator > 0 else 0


def get_office_candidates_ids(office_id, tally_id):
    """Get the candidates id's for candidates in these result forms filtered by
    office id and tally id.

    If the result form is a component ballot the candidates ids from the
    general ballot must be combined with the candidates ids from the component
    ballot.

    :returns: A list of candidates ids.
    """
    result_forms = ResultForm.objects.filter(
        office_id=office_id,
        tally_id=tally_id)
    ballot_candidate_id_field_name =\
        'ballot__sc_general__ballot_component__candidates__id'
    default_case_value = 0

    candidate_id_map =\
        result_forms\
        .aggregate(
            ballot_component_candidate_ids=ArrayAgg(
                Case(
                    When(
                        ballot__sc_general__ballot_component__isnull=False,
                        then=ballot_candidate_id_field_name),
                    default=V(default_case_value)),
                distinct=True),
            ballot_candidate_ids=ArrayAgg(
                Case(
                    When(
                        ballot__candidates__id__isnull=False,
                        then='ballot__candidates__id'),
                    default=V(default_case_value)),
                distinct=True))

    candidate_ids =\
        candidate_id_map['ballot_component_candidate_ids'] +\
        candidate_id_map['ballot_candidate_ids']

    # Remove default_case_value from candidate_ids
    candidate_ids =\
        list(filter(
            lambda candidate_id:
                candidate_id != default_case_value, candidate_ids))

    return candidate_ids


class ProgressReport(object):

    def __init__(self, tally_id):
        self.tally_id = tally_id
        self.filtered_queryset = self.queryset = \
            ResultForm.distinct_forms(tally_id)

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

    def numerator(self, filtered_queryset=None):
        if not filtered_queryset:
            return self.get_filtered_queryset().count()

        return filtered_queryset.count()

    number = property(numerator)

    def denominator(self, queryset=None):
        if not queryset:
            return self.get_queryset().count()

        return queryset.count()

    total = property(denominator)

    def percentage_value(self, queryset=None, filtered_queryset=None):
        if self.denominator(queryset) <= 0:
            return _(u"No results")

        return rounded_percent(self.numerator(filtered_queryset),
                               self.denominator(queryset))

    percentage = property(percentage_value)

    def for_ballot(self, ballot=None, form_ballot_numbers=None):
        if not form_ballot_numbers:
            form_ballot_numbers = ballot.form_ballot_numbers

        filtered_queryset = self.get_filtered_queryset().filter(
            ballot__number__in=form_ballot_numbers,
            tally__id=self.tally_id)
        queryset = self.get_queryset().filter(
            ballot__number__in=form_ballot_numbers,
            tally__id=self.tally_id)

        denominator = queryset.count()
        number = filtered_queryset.count()
        percentage = rounded_percent(number, denominator) if denominator > 0\
            else _(u"No results")

        return {'denominator': denominator,
                'number': number,
                'percentage': percentage}

    def for_center_office(self, office, query_valid_votes=False):
        filtered_queryset = self.get_filtered_queryset().filter(
            center__office=office)
        count = filtered_queryset.count()

        if query_valid_votes:
            filtered_queryset =\
                filtered_queryset\
                .values('reconciliationform__number_valid_votes')\
                .annotate(
                    valid_votes=Coalesce(
                        Sum('reconciliationform__number_valid_votes'), V(0)))\
                .first()

            count =\
                filtered_queryset['valid_votes'] if filtered_queryset else 0

        return count


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

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.ARCHIVED, tally_id=self.tally_id)


class IntakeProgressReport(ProgressReport):
    label = _(u"Intake")

    def __init__(self, tally_id):
        super(IntakeProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.INTAKE, tally_id=self.tally_id)


class ClearanceProgressReport(ProgressReport):
    label = _(u"Clearance")

    def __init__(self, tally_id):
        super(ClearanceProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.CLEARANCE, tally_id=self.tally_id)


class DataEntry1ProgressReport(ProgressReport):
    label = _(u"Data Entry 1")

    def __init__(self, tally_id):
        super(DataEntry1ProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.DATA_ENTRY_1, tally_id=self.tally_id)


class DataEntry2ProgressReport(ProgressReport):
    label = _(u"Data Entry 2")

    def __init__(self, tally_id):
        super(DataEntry2ProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.DATA_ENTRY_2, tally_id=self.tally_id)


class CorrectionProgressReport(ProgressReport):
    label = _(u"Correction")

    def __init__(self, tally_id):
        super(CorrectionProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.CORRECTION, tally_id=self.tally_id)


class QualityControlProgressReport(ProgressReport):
    label = _(u"Quality Control")

    def __init__(self, tally_id):
        super(QualityControlProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.QUALITY_CONTROL, tally_id=self.tally_id)


class AuditProgressReport(ProgressReport):
    label = _(u"Audit")

    def __init__(self, tally_id):
        super(AuditProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.AUDIT, tally_id=self.tally_id)


class NotRecievedProgressReport(ProgressReport):
    label = _(u"Not Received")

    def __init__(self, tally_id):
        super(NotRecievedProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.forms_in_state(
            FormState.UNSUBMITTED, tally_id=self.tally_id)


class ValidVotesProgressReport(ProgressReport):
    label = _(u"Valid Votes")

    def __init__(self, tally_id):
        super(ValidVotesProgressReport, self).__init__(tally_id)

        self.filtered_queryset = ResultForm.objects.filter(
            tally_id=self.tally_id,
            reconciliationform__isnull=False)
