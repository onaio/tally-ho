import json

from django.db.models import Q, Subquery, OuterRef, IntegerField, F
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone

from django_datatables_view.base_datatable_view import BaseDatatableView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.views.constants import race_type_query_param, form_state_query_param
from tally_ho.libs.models.enums.form_state import FormState, form_state_shift_path
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale
)
from tally_ho.libs.views import mixins
from urllib.parse import urlencode


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
        ballot_number = self.request.POST.get('ballot[value]', None)
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.POST.get('search[value]')

        requested_form_state = self.request.GET.get(form_state_query_param, None)
        requested_race_type = self.request.GET.get(race_type_query_param, None)

        if requested_race_type:
            race_enum_key = requested_race_type.upper()
            if race_enum_key in RaceType.__members__:
                specified_race_type = RaceType[race_enum_key]
                qs = qs.filter(ballot__race_type=specified_race_type)
        if requested_form_state:
            state_enum_key = requested_form_state.upper()
            if state_enum_key in FormState.__members__:
                specified_form_state = FormState[state_enum_key]
                # get forms that are not in this state or future possible states depending
                # on how the form state transitions through the stages.
                excluded_form_states = form_state_shift_path[form_state_shift_path.index(specified_form_state):]
                qs = qs.exclude(form_state__in=excluded_form_states)

        station_id_query = \
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
        # TODO - how is this form state used?
        form_state = kwargs.get('state')
        tally_id = kwargs.get('tally_id')

        requested_form_state = self.request.GET.get(form_state_query_param, None)
        requested_race_type = self.request.GET.get(race_type_query_param, None)

        error = self.request.session.get('error_message')
        language_de = get_datatables_language_de_from_locale(self.request)
        download_url = '/ajax/download-result-forms/'

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

        params = {}
        if requested_form_state:
            params[form_state_query_param] = requested_form_state
        if requested_race_type:
            params[race_type_query_param] = requested_race_type
        query_param_string = urlencode(params)
        remote_data_url = reverse(
                                      'form-list-data',
                                      kwargs={'tally_id': tally_id})
        if query_param_string:
            remote_data_url = f"{remote_data_url}?{query_param_string}"

        return self.render_to_response(
            self.get_context_data(header_text=_('Form List'),
                                  remote_url=remote_data_url,
                                  tally_id=tally_id,
                                  error_message=_(error) if error else None,
                                  show_create_form_button=True,
                                  result_forms_download_url=download_url,
                                  languageDE=language_de))


class FormNotReceivedListView(FormListView):
    group_required = groups.SUPER_ADMINISTRATOR

    def get(self, *args, **kwargs):
        format_ = kwargs.get('format')
        tally_id = kwargs.get('tally_id')
        language_de = get_datatables_language_de_from_locale(self.request)

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
                                  tally_id=tally_id,
                                  languageDE=language_de))


class FormNotReceivedDataView(FormListDataView):
    def filter_queryset(self, qs):
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.POST.get('search[value]')
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
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            header_text=_('Forms for Race %s' % ballot),
            none=True,
            tally_id=tally_id,
            remote_url=reverse('forms-for-race-data',
                               args=[tally_id, ballot]),
            languageDE=language_de))


def get_result_forms(request):
    """
    Builds a json object of result forms.

    :param request: The request object containing the tally id.

    returns: A JSON response of result forms
    """
    tally_id = json.loads(request.GET.get('data')).get('tally_id')
    race_types = json.loads(request.GET.get('data')).get('race_types')
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

    form_list = ResultForm.objects.filter(
        tally__id=tally_id,
        ballot__race_type__in=race_types)\
        .annotate(
            center_code=F('center__code'),
            office_name=F('center__office__name'),
            office_number=F('center__office__number'),
            region_id=F('center__office__region__id'),
            region_name=F('center__office__region__name'),
            station_id=station_id_query)\
        .values(
            'id',
            'tally_id',
            'barcode',
            'station_id',
            'station_number',
            'center_code',
            'office_id',
            'office_name',
            'office_number',
            'region_id',
            'region_name',
            'form_state',
    )

    for form in form_list:
        if isinstance(form['form_state'], FormState):
            form['form_state'] = form['form_state'].label

    return JsonResponse(
        data={'data': list(form_list), 'created_at': timezone.now()},
        safe=False)
