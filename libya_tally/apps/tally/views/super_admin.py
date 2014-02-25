from django.core.exceptions import SuspiciousOperation

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.template import loader, RequestContext
from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _

from djqscsv import render_to_csv_response
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.models.audit import Audit
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.models.station import Station
from libya_tally.libs.models.enums.audit_resolution import\
    AuditResolution
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.views.exports import export_to_csv_response, \
    get_result_export_response


ALL = '__all__'


def duplicates():
    dupes = ResultForm.objects.values(
        'center', 'ballot', 'station_number').annotate(
        Count('id')).order_by().filter(id__count__gt=1).filter(
        center__isnull=False, ballot__isnull=False,
        station_number__isnull=False).exclude(form_state=FormState.UNSUBMITTED)

    pks = []
    for item in dupes:
        pks.extend([r.pk for r in ResultForm.objects.filter(
            center=item['center'], ballot=item['ballot'],
            station_number=item['station_number'])])

    return ResultForm.objects.filter(pk__in=pks)


def paging(form_list, request):
    paginator = Paginator(form_list, 100)
    page = request.GET.get('page')

    try:
        forms = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        forms = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page.
        forms = paginator.page(paginator.num_pages)

    return forms


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
        'center__office__name',
        'sub_constituency__code',
        'center__name',
        'center__code',
        'gender',
        'registrants',
        'modified_date',
    )
    display_fields = (
        ('center__office__name', 'center_office'),
        ('sub_constituency__code', 'sub_constituency_code'),
        ('center__name', 'center_name'),
        ('center__code', 'center_code'),
        ('gender', 'gender_name'),
        ('registrants', 'registrants'),
        ('modified_date', 'modified_date_formatted'),
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
        'center__office__name',
        'center__office__number',
        'ballot__number',
        'ballot__race_type',
        'form_state',
        'modified_date',
    )
    display_fields = (
        ('barcode', 'barcode'),
        ('center__code', 'center_code'),
        ('station_number', 'station_number'),
        ('center__office__name', 'center_office'),
        ('center__office__number', 'center_office_number'),
        ('ballot__number', 'ballot_number'),
        ('form_state', 'form_state_name'),
        ('ballot__race_type', 'ballot_race_type_name'),
        ('modified_date', 'modified_date_formatted'),
    )


class FormListView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/forms.html"

    def get(self, *args, **kwargs):
        form_state = kwargs.get('state')

        if form_state:
            if form_state == ALL:
                form_list = ResultForm.objects.all()
            else:
                form_state = FormState.get(form_state)
                form_list = ResultForm.objects.filter(
                    form_state=form_state.value)

            form_list = form_list.values(
                'barcode', 'form_state', 'gender', 'station_number',
                'center__sub_constituency__code',
                'center__code',
                'ballot__race_type').order_by('barcode')

            return render_to_csv_response(form_list)

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

        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(
            forms=forms))


class FormDuplicatesView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/form_duplicates.html"

    def get(self, *args, **kwargs):
        form_list = duplicates()

        forms = paging(form_list, self.request)

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
        'ballot__number',
        'center__office__name',
        'center__office__number',
        'ballot__race_type',
        'form_state',
        'rejected_count',
        'modified_date',
    )
    display_fields = (
        ('barcode', 'barcode'),
        ('center__code', 'center_code'),
        ('station_number', 'station_number'),
        ('ballot__number', 'ballot_number'),
        ('center__office__name', 'center_office'),
        ('center__office__number', 'center_office_number'),
        ('ballot__race_type', 'ballot_race_type_name'),
        ('form_state', 'form_state_name'),
        ('rejected_count', 'rejected_count'),
        ('modified_date', 'modified_date_formatted'),
    )


class FormDuplicatesDataView(FormProgressDataView):
    queryset = duplicates()


class FormActionView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.ReverseSuccessURLMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/form_action.html"
    success_url = 'form-action-view'

    def get(self, *args, **kwargs):
        audits = Audit.objects.filter(
            active=True,
            reviewed_supervisor=True,
            resolution_recommendation=
            AuditResolution.MAKE_AVAILABLE_FOR_ARCHIVE).all()

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


class FormNotReceivedListView(LoginRequiredMixin,
                              mixins.GroupRequiredMixin,
                              TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/forms_not_received.html"
    header_template_name = "tally/super_admin/forms_not_received_header.html"
    queryset = ResultForm.unsubmitted_result_forms()

    headers = [
        _(u'Barcode'),
        _(u'Center Code'),
        _(u'Station Number'),
        _(u'Office'),
        _(u'Office Number'),
        _(u'Voting District'),
        _(u'Race Type'),
        _(u'Form State'),
        _(u'Last Modified')
    ]

    def get(self, *args, **kwargs):
        fmt = kwargs.get('format')
        if fmt == 'csv':
            filename = 'forms-not-received.csv'

            # get translated headers
            context = RequestContext(self.request)
            t = loader.get_template(self.header_template_name)
            headers = t.render(context).strip().split(',')

            fields = [name
                      for f, name in FormNotReceivedDataView.display_fields]

            return export_to_csv_response(
                self.queryset, headers, fields, filename)
        return super(FormNotReceivedListView, self).get(*args, **kwargs)


class FormNotReceivedDataView(FormListDataView):
    queryset = ResultForm.unsubmitted_result_forms()


class ResultExportView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/result_export.html"

    def get(self, *args, **kwargs):
        report = kwargs.get('report')
        if report:
            return get_result_export_response(report)
        return super(ResultExportView, self).get(*args, **kwargs)
