from django.core.exceptions import SuspiciousOperation
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.models.audit import Audit
from libya_tally.apps.tally.models.clearance import Clearance
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.models.station import Station
from libya_tally.libs.models.enums.audit_resolution import\
    AuditResolution
from libya_tally.libs.models.enums.clearance_resolution import\
    ClearanceResolution
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/home.html"

    def get(self, *args, **kwargs):
        group_logins = [g.lower().replace(' ', '_') for g in groups.GROUPS]

        return self.render_to_response(self.get_context_data(
            groups=group_logins))


class CenterListDataView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.DatatablesDisplayFieldsMixin,
                         DatatablesView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Station
    fields = (
        'center__office',
        'sub_constituency__code',
        'center__name',
        'center__code',
        'gender',
        'registrants',
        'modified_date',
    )
    display_fields = (
        ('center__office', 'center_office'),
        ('sub_constituency__code', 'sub_constituency_code'),
        ('center__name', 'center_name'),
        ('center__code', 'center_code'),
        ('gender', 'gender_name'),
        ('registrants', 'registrants'),
        ('modified_date', 'modified_date'),
    )


class CenterListView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/centers.html"

    def get(self, *args, **kwargs):
        station_list = Station.objects.all()
        paginator = Paginator(station_list, 100)
        page = self.request.GET.get('page')

        try:
            stations = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            stations = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page.
            stations = paginator.page(paginator.num_pages)

        return self.render_to_response(self.get_context_data(
            stations=stations))


class FormListDataView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.DatatablesDisplayFieldsMixin,
                       DatatablesView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    fields = (
        'barcode',
        'center__code',
        'station_number',
        'center__office',
        'ballot__number',
        'ballot__race_type',
        'modified_date',
    )
    display_fields = (
        ('barcode', 'barcode_padded'),
        ('center__code', 'center_code'),
        ('station_number', 'station_number'),
        ('center__office', 'center_office'),
        ('ballot__number', 'ballot_number'),
        ('ballot__race_type', 'ballot_race_type_name'),
        ('modified_date', 'modified_date'),
    )


class FormListView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/forms.html"

    def get(self, *args, **kwargs):
        form_list = ResultForm.objects.all()
        paginator = Paginator(form_list, 100)
        page = self.request.GET.get('page')

        try:
            forms = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            forms = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page.
            forms = paginator.page(paginator.num_pages)

        return self.render_to_response(self.get_context_data(
            forms=forms))


class FormProgressView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/form_progress.html"

    def get(self, *args, **kwargs):
        form_list = ResultForm.objects.exclude(
            form_state=FormState.UNSUBMITTED)
        paginator = Paginator(form_list, 100)
        page = self.request.GET.get('page')

        try:
            forms = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            forms = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page.
            forms = paginator.page(paginator.num_pages)

        return self.render_to_response(self.get_context_data(
            forms=forms))


class FormProgressDataView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.DatatablesDisplayFieldsMixin,
                           DatatablesView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    queryset = ResultForm.objects.exclude(form_state=FormState.UNSUBMITTED)
    fields = (
        'barcode',
        'center__code',
        'station_number',
        'center__office',
        'ballot__race_type',
        'form_state',
        'rejected_count',
        'modified_date',
    )
    display_fields = (
        ('barcode', 'barcode_padded'),
        ('center__code', 'center_code'),
        ('station_number', 'station_number'),
        ('center__office', 'center_office'),
        ('ballot__race_type', 'ballot_race_type_name'),
        ('form_state', 'form_state_name'),
        ('rejected_count', 'rejected_count'),
        ('modified_date', 'modified_date'),
    )


class FormActionView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.ReverseSuccessURLMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/form_action.html"
    success_url = 'form-action-view'

    def get(self, *args, **kwargs):
        audit_list = Audit.objects.filter(
            active=True,
            reviewed_supervisor=True,
            resolution_recommendation=
            AuditResolution.MAKE_AVAILABLE_FOR_ARCHIVE).all()
        clearance_list = Clearance.objects.filter(
            active=True,
            reviewed_supervisor=True,
            resolution_recommendation=ClearanceResolution.RESET_TO_PREINTAKE
        ).all()

        return self.render_to_response(self.get_context_data(
            audit_forms=audit_list,
            clearance_forms=clearance_list))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = post_data.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)

        if 'review' in post_data:
            self.request.session['result_form'] = pk

            if result_form.form_state == FormState.AUDIT:
                return redirect('audit-review')
            elif result_form.form_state == FormState.CLEARANCE:
                return redirect('clearance-review')
        elif 'confirm' in post_data:
            if result_form.form_state == FormState.AUDIT:
                result_form.form_state = FormState.DATA_ENTRY_1
                audit = result_form.audit
                audit.active = False
                audit.save()
            elif result_form.form_state == FormState.CLEARANCE:
                result_form.form_state = FormState.INTAKE
                clearance = result_form.clearance
                clearance.active = False
                clearance.save()

            result_form.save()

            return redirect(self.success_url)
        else:
            raise SuspiciousOperation('Unknown POST response type')
