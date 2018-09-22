from django.core.exceptions import SuspiciousOperation
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.db.utils import ProgrammingError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView
from django.utils.translation import ugettext_lazy as _
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.remove_center_form import RemoveCenterForm
from tally_ho.apps.tally.forms.remove_station_form import RemoveStationForm
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.audit_resolution import\
    AuditResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.collections import flatten
from tally_ho.libs.views import mixins
from tally_ho.libs.views.exports import get_result_export_response


def duplicates(qs):
    """Build a list of result forms that are duplicates considering only forms
    that are not unsubmitted.

    :returns: A list of result forms in the system that are duplicates.
    """
    try:
        dupes = ResultForm.objects.values(
            'center', 'ballot', 'station_number').annotate(
            Count('id')).order_by().filter(id__count__gt=1).filter(
            center__isnull=False, ballot__isnull=False,
            station_number__isnull=False).exclude(
                form_state=FormState.UNSUBMITTED)

        pks = flatten([map(lambda x: x['id'], ResultForm.objects.filter(
            center=item['center'], ballot=item['ballot'],
            station_number=item['station_number']).values('id'))
            for item in dupes])

        return qs.filter(pk__in=pks)
    except ProgrammingError:
        return []


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/home.html"

    def get(self, *args, **kwargs):
        group_logins = [g.lower().replace(' ', '_') for g in groups.GROUPS]

        return self.render_to_response(self.get_context_data(
            groups=group_logins))


class FormProgressView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_progress.html"


class FormDuplicatesView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_duplicates.html"


class FormProgressDataView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    columns = (
        'barcode',
        'center.code',
        'station_number',
        'ballot.number',
        'center.office.name',
        'center.office.number',
        'ballot.race_type',
        'form_state',
        'rejected_count',
        'modified_date',
    )

    def filter_queryset(self, qs):
        return qs.exclude(form_state=FormState.UNSUBMITTED)


class FormDuplicatesDataView(FormProgressDataView):
    def filter_queryset(self, qs):
        return duplicates(qs)


class FormActionView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.ReverseSuccessURLMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_action.html"
    success_url = 'form-action-view'

    def get(self, *args, **kwargs):
        audits = Audit.objects.filter(
            active=True,
            reviewed_supervisor=True,
            resolution_recommendation=AuditResolution.
            MAKE_AVAILABLE_FOR_ARCHIVE).all()

        return self.render_to_response(self.get_context_data(
            audits=audits))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = self.request.session['result_form'] = post_data.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)

        if 'review' in post_data:
            return redirect('audit-review')
        elif 'confirm' in post_data:
            result_form.reject()
            result_form.skip_quarantine_checks = True
            result_form.save()

            audit = result_form.audit
            audit.active = False
            audit.save()

            return redirect(self.success_url)
        else:
            raise SuspiciousOperation('Unknown POST response type')


class ResultExportView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/result_export.html"

    def get(self, *args, **kwargs):
        report = kwargs.get('report')
        if report:
            return get_result_export_response(report)
        return super(ResultExportView, self).get(*args, **kwargs)


class RemoveCenterView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       SuccessMessageMixin,
                       FormView):
    form_class = RemoveCenterForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_center.html"
    success_url = 'super-administrator'
    success_message = _(u"Center Successfully Removed.")

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            center = form.save()
            self.success_message = _(
                u"Successfully removed center %(center)s"
                % {'center': center.code})
            return self.form_valid(form)
        return self.form_invalid(form)


class RemoveStationView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        SuccessMessageMixin,
                        FormView):
    form_class = RemoveStationForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_station.html"
    success_url = 'super-administrator'
    success_message = _(u"Station Successfully Removed.")

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            station = form.save()
            self.success_message = _(
                u"Successfully removed station %(station)s from "
                u"center %(center)s." % {'center': station.center.code,
                                         'station': station.station_number})
            return self.form_valid(form)
        return self.form_invalid(form)
