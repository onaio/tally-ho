from django.template import loader, RequestContext
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from djqscsv import render_to_csv_response
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from tally_system.apps.tally.models.result_form import ResultForm
from tally_system.libs.models.enums.form_state import FormState
from tally_system.libs.permissions import groups
from tally_system.libs.views import mixins
from tally_system.libs.views.exports import export_to_csv_response
from tally_system.libs.views.pagination import paging


ALL = '__all__'


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
    template_name = "super_admin/forms.html"

    def get(self, *args, **kwargs):
        form_state = kwargs.get('state')

        if form_state:
            if form_state == ALL:
                form_list = ResultForm.objects.all()
            else:
                form_state = FormState.get(form_state)
                form_list = ResultForm.forms_in_state(form_state.value)

            form_list = form_list.values(
                'barcode', 'form_state', 'gender', 'station_number',
                'center__sub_constituency__code',
                'center__code',
                'ballot__race_type').order_by('barcode')

            return render_to_csv_response(form_list)

        form_list = ResultForm.objects.all()
        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(
            forms=forms))


class FormNotReceivedListView(LoginRequiredMixin,
                              mixins.GroupRequiredMixin,
                              TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/forms_not_received.html"
    header_template_name = "super_admin/forms_not_received_header.html"
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
