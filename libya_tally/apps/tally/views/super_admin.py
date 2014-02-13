from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseBadRequest
from django.views.generic import TemplateView
from eztables.forms import DatatablesForm
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.models.station import Station
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
        ('center__code', '_center_code'),
        ('station_number', 'station_number'),
        ('center__office', '_center_office'),
        ('ballot__number', '_ballot_number'),
        ('ballot__race_type', '_ballot_race_type_name'),
        ('modified_date', 'modified_date'),
    )

    def get_row(self, row):
        '''Format a single row (if necessary)'''

        data = {}
        for field, name in self.display_fields:
            data[field] = getattr(row, name)
        return [data[field] for field in self.fields]

    def process_dt_response(self, data):
        self.form = DatatablesForm(data)
        if self.form.is_valid():
            self.object_list = self.get_queryset()
            return self.render_to_response(self.form)
        else:
            return HttpResponseBadRequest()


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
