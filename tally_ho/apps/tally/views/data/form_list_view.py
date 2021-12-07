from django.db.models import Q, Subquery, OuterRef, IntegerField
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from django.urls import reverse

from django_datatables_view.base_datatable_view import BaseDatatableView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


ALL = '__all__'


class FormListDataView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    columns = (
        'barcode',
        'center.code',
        'station_id',
        'station_number',
        'center.office.name',
        'center.office.number',
        'center.office.region.name',
        'ballot.number',
        'ballot.race_type',
        'form_state',
        'modified_date',
        'action'
    )

    def render_column(self, row, column):
        if column == 'modified_date':
            return row.modified_date.strftime('%a, %d %b %Y %H:%M:%S %Z')
        if column == 'action':
            return row.get_action_button
        else:
            return super(FormListDataView, self).render_column(row, column)

    def filter_queryset(self, qs):
        ballot_number = self.request.GET.get('ballot[value]', None)
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.GET.get('search[value]', None)
        station_id_query =\
            Subquery(
                Station.objects.filter(
                    tally__id=tally_id,
                    center__code=OuterRef(
                        'center__code'),
                    station_number=OuterRef(
                        'station_number'))
                .values('id')[:1],
                output_field=IntegerField())

        if tally_id:
            qs =\
                qs.filter(tally__id=tally_id)\
                .annotate(
                    station_id=station_id_query,
                )

        if ballot_number:
            ballot = Ballot.objects.get(number=ballot_number,
                                        tally__id=tally_id)
            qs = qs.filter(
                ballot__number__in=ballot.form_ballot_numbers)

        if keyword:
            qs = qs.filter(Q(barcode__contains=keyword) |
                           Q(center__code__contains=keyword) |
                           Q(station_id__contains=keyword) |
                           Q(center__office__region__name__contains=keyword) |
                           Q(center__office__name__contains=keyword) |
                           Q(center__office__number__contains=keyword) |
                           Q(station_number__contains=keyword) |
                           Q(ballot__number__contains=keyword))

        return qs


class FormListView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.TallyAccessMixin,
                   TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/forms.html"

    def get(self, *args, **kwargs):
        form_state = kwargs.get('state')
        tally_id = kwargs.get('tally_id')
        error = self.request.session.get('error_message')

        if error:
            del self.request.session['error_message']

        if form_state:
            if form_state == ALL:
                form_list = ResultForm.objects.filter(tally__id=tally_id)
            else:
                form_state = FormState[form_state.upper()]
                form_list = ResultForm.forms_in_state(form_state.value,
                                                      tally_id=tally_id)

            form_list = form_list.values(
                'barcode', 'form_state', 'gender', 'station_number',
                'center__sub_constituency__code',
                'center__code',
                'ballot__race_type').order_by('barcode')

            return render_to_csv_response(form_list)

        return self.render_to_response(
            self.get_context_data(header_text=_('Form List'),
                                  remote_url=reverse(
                                      'form-list-data',
                                      kwargs={'tally_id': tally_id}),
                                  tally_id=tally_id,
                                  error_message=_(error) if error else None,
                                  show_create_form_button=True))


class FormNotReceivedListView(FormListView):
    group_required = groups.SUPER_ADMINISTRATOR

    def get(self, *args, **kwargs):
        format_ = kwargs.get('format')
        tally_id = kwargs.get('tally_id')

        if format_ == 'csv':
            form_list = ResultForm.forms_in_state(FormState.UNSUBMITTED,
                                                  tally_id=tally_id)
            return render_to_csv_response(form_list)

        return self.render_to_response(
            self.get_context_data(header_text=_('Forms Not Received'),
                                  custom=True,
                                  remote_url=reverse(
                                      'form-not-received-data',
                                      kwargs={'tally_id': tally_id}),
                                  tally_id=tally_id))


class FormNotReceivedDataView(FormListDataView):
    def filter_queryset(self, qs):
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.GET.get('search[value]', None)
        qs = ResultForm.forms_in_state(
            FormState.UNSUBMITTED,
            tally_id=tally_id)
        if keyword:
            qs = qs.filter(Q(barcode__contains=keyword) |
                           Q(center__code__contains=keyword) |
                           Q(center__office__region__name__contains=keyword) |
                           Q(center__office__name__contains=keyword) |
                           Q(center__office__number__contains=keyword) |
                           Q(station_number__contains=keyword) |
                           Q(ballot__number__contains=keyword))
        return qs


class FormsForRaceView(FormListView):
    group_require = groups.SUPER_ADMINISTRATOR

    def get(self, *args, **kwargs):
        ballot = kwargs.get('ballot')
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            header_text=_('Forms for Race %s' % ballot),
            none=True,
            tally_id=tally_id,
            remote_url=reverse('forms-for-race-data',
                               args=[tally_id, ballot])))
