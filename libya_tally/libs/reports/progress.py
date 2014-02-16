from django.db.models import Q
from django.db.models.query import QuerySet
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState


class ProgressReport(object):
    queryset = ResultForm.objects.all()
    filtered_queryset = None

    def get_queryset(self):
        if self.queryset is None or not isinstance(self.queryset, QuerySet):
            raise ImproperlyConfigured(
                u"`queryset needs to be of instance QuerySet`")

        return self.queryset

    def get_filtered_queryset(self):
        if not isinstance(self.filtered_queryset, QuerySet):
            raise ImproperlyConfigured(
                u"`queryset needs to be of instance QuerySet`")

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
        return '%s%%' % round(
            100 * (self.numerator() / float(self.denominator())), 2)

    percentage = property(percentage_value)

    def for_center_office(self, office):
        obj = self.__class__()
        obj.filtered_queryset = \
            self.get_filtered_queryset().filter(office=office)
        obj.queryset = self.get_queryset().filter(office=office)

        return obj


class ExpectedProgressReport(ProgressReport):
    filtered_queryset = ResultForm.objects.all()
    label = _(u"Expected")


class IntakenProgressReport(ProgressReport):
    filtered_queryset = ResultForm.objects.exclude(
        Q(form_state=FormState.UNSUBMITTED) | Q(form_state=FormState.INTAKE))
    label = _(u"Intaken")


class ArchivedProgressReport(ProgressReport):
    filtered_queryset = ResultForm.objects.filter(
        form_state=FormState.ARCHIVED)
    label = _(u"Archived")


class ClearanceProgressReport(ProgressReport):
    filtered_queryset = ResultForm.objects.filter(
        form_state=FormState.CLEARANCE)
    label = _(u"Clearance")


class AuditProgressReport(ProgressReport):
    filtered_queryset = ResultForm.objects.filter(
        form_state=FormState.AUDIT)
    label = _(u"Audit")


class NotRecievedProgressReport(ProgressReport):
    filtered_queryset = ResultForm.objects.filter(
        form_state=FormState.UNSUBMITTED)
    label = _(u"Not Received")
