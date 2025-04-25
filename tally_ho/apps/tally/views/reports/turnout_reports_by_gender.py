from django.shortcuts import render
from django.urls import reverse
from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models import (
    Station, ResultForm, Result, ReconciliationForm
    )
from tally_ho.libs.reports.list_base_data_view import \
    NoneQsBaseDataView
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import \
    get_datatables_language_de_from_locale
from tally_ho.libs.views import mixins
from django.db.models import (
    IntegerField, Subquery, F, OuterRef, Sum, Case, When, Value as V, CharField
)
from django.db.models.functions import Coalesce

def station_gender_query(
        tally_id, center_code_filter_name, station_number_filter_name):
    """
    Get the gender of the station
    :param tally_id: The id of the tally
    :param center_code_filter_name: The name of the center code filter
    :param station_number_filter_name: The name of the station number filter
    :return: The gender of the station
    """
    return Subquery(
        Station.objects.filter(
            tally__id=tally_id,
            center__code=OuterRef(center_code_filter_name),
            station_number=OuterRef(station_number_filter_name))
        .values('gender')[:1],
        output_field=IntegerField()
    )

def station_registrants_query(
        tally_id, center_code_filter_name, station_number_filter_name):
    """
    Get the registrants of the station
    :param tally_id: The id of the tally
    :param center_code_filter_name: The name of the center code filter
    :param station_number_filter_name: The name of the station number filter
    :return: The registrants of the station
    """
    return Subquery(
        Station.objects.filter(
            tally__id=tally_id,
            center__code=OuterRef(center_code_filter_name),
            station_number=OuterRef(station_number_filter_name))
        .values('registrants')[:1],
        output_field=IntegerField()
    )

def get_invalid_votes_from_reconciliation_form(
        tally_id,
        admin_level_filter_name,
        admit_area_name,
        sub_race_type
    ):
    """
    Get the invalid votes from the reconciliation form
    :param tally_id: The id of the tally
    :param admin_level_filter_name: The name of the admin level filter
    :param admit_area_name: The name of the admit area
    :param sub_race_type: The type of the sub race
    :return: The invalid votes from the reconciliation form
    """
    area_filter_map =\
                {
                    f"result_form__{admin_level_filter_name}":
                    admit_area_name
                }
    return ReconciliationForm.objects.filter(
        result_form__tally__id=tally_id,
        **area_filter_map,
        result_form__ballot__electrol_race__ballot_name=sub_race_type,
        result_form__form_state=FormState.ARCHIVED,
        entry_version=EntryVersion.FINAL,
        active=True
    ).aggregate(
        invalid_votes=Coalesce(Sum('number_invalid_votes'), 0)
    ).get('invalid_votes')

def group_data_by_gender(
        tally_id,
        admin_level_filter_name
    ):
    """
    Group the data by gender
    :param tally_id: The id of the tally
    :param admin_level_filter_name: The name of the admin level filter
    :return: The grouped data by gender
    """
    return ResultForm.objects.filter(
        tally__id=tally_id,
    ).annotate(
        station_gender_code=station_gender_query(
            tally_id,
            center_code_filter_name='center__code',
            station_number_filter_name='station_number'),
        station_registrants=station_registrants_query(
            tally_id,
            center_code_filter_name='center__code',
            station_number_filter_name='station_number'),
        station_gender=Case(
            When(station_gender_code=0,
                then=V('Man')),
            default=V('Woman'),
            output_field=CharField()),
        admit_area_name=F(admin_level_filter_name),
        sub_race_type=F('ballot__electrol_race__ballot_name')
    ).values(
        'admit_area_name',
        'station_gender_code',
        'station_gender',
        'sub_race_type'
    ).annotate(
        total_registrants=Sum('station_registrants')
    )

def get_voters_by_gender(
        tally_id,
        admin_level_filter_name,
        admit_area_name,
        sub_race_type,
        station_gender_code
    ):
    """
    Get the voters by gender
    :param tally_id: The id of the tally
    :param admin_level_filter_name: The name of the admin level filter
    :param admit_area_name: The name of the admit area
    :param sub_race_type: The type of the sub race
    :param station_gender_code: The code of the station gender
    :return: The voters by gender
    """
    area_filter_map =\
                {
                    f"result_form__{admin_level_filter_name}":
                    admit_area_name
                }
    voters = Result.objects.filter(
            result_form__tally__id=tally_id,
            **area_filter_map,
            result_form__ballot__electrol_race__ballot_name=\
                sub_race_type,
            result_form__form_state=FormState.ARCHIVED,
            entry_version=EntryVersion.FINAL,
            active=True,
    ).annotate(
        station_gender_code=station_gender_query(
            tally_id,
            center_code_filter_name='result_form__center__code',
            station_number_filter_name='result_form__station_number'),
        station_registrants=station_registrants_query(
            tally_id,
            center_code_filter_name='result_form__center__code',
            station_number_filter_name='result_form__station_number'),
    ).filter(
        station_gender_code=station_gender_code
    ).aggregate(
        voters=Coalesce(Sum('votes'), 0)
    ).get('voters')
    return voters

class TurnoutReportByGenderAndAdminAreasDataView(
    LoginRequiredMixin, mixins.GroupRequiredMixin, mixins.TallyAccessMixin,
    NoneQsBaseDataView
    ):
    group_required = groups.TALLY_MANAGER
    columns = (
        "admit_area_name",
        "sub_race",
        "human",
        "voters",
        "registrants",
        "turnout"
    )

    def get_initial_queryset(self):
        tally_id = self.kwargs.get('tally_id')
        admin_level = self.kwargs.get('admin_level')
        admin_level_filter_name = None

        if admin_level == "office":
            admin_level_filter_name = 'office__name'
        elif admin_level == "constituency":
            admin_level_filter_name = 'center__constituency__name'
        elif admin_level == "sub_constituency":
            admin_level_filter_name = 'center__sub_constituency__name'
        else:
            admin_level_filter_name = 'office__region__name'

        ret_value = []

        turnout_data = group_data_by_gender(
            tally_id,
            admin_level_filter_name
        )
        for data in turnout_data:
            response = {}
            voters = get_voters_by_gender(
                tally_id,
                admin_level_filter_name,
                data.get('admit_area_name'),
                data.get('sub_race_type'),
                data.get('station_gender_code')
            )
            invalid_votes = get_invalid_votes_from_reconciliation_form(
                tally_id,
                admin_level_filter_name,
                data.get('admit_area_name'),
                data.get('sub_race_type')
            )
            voters = voters + invalid_votes
            response['admit_area_name'] = data.get('admit_area_name')
            response['sub_race'] = data.get('sub_race_type')
            response['human'] = data.get('station_gender')
            response['voters'] = voters
            response['registrants'] = data.get('total_registrants')
            response['turnout'] =\
                round(100 * voters / response['registrants'], 2)
            ret_value.append(response)
        ret_value = sorted(ret_value, key=lambda x: -x['turnout'])
        return ret_value

    def get_aggregate(self, data):
        aggregate = get_aggregate_data(data)
        return self.prepare_results([aggregate])


    def render_column(self, row, column):
        if column in self.columns:
            col_value = row[column]
            return str(
                '<td class="center">'
                f'{col_value}</td>'
                )
        else:
            return super(
                TurnoutReportByGenderAndAdminAreasDataView, self
                ).render_column(row, column)

def get_aggregate_data(data):
    aggregate = {}
    aggregate['admit_area_name'] = "Total"
    aggregate["sub_race"] = "N/A"
    aggregate["human"] = "N/A"
    aggregate["voters"] = sum(
        entry['voters'] for entry in
        data
        )
    aggregate["registrants"] = sum(
        entry['registrants'] for entry in
        data
        )
    aggregate["turnout"] =\
        round(100 * aggregate["voters"] / aggregate["registrants"], 2)
    return aggregate

class TurnoutReportByGenderAndAdminAreasView(
    LoginRequiredMixin,
    mixins.GroupRequiredMixin,
    TemplateView
    ):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/turnout_report_by_gender_and_admin_area.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        admin_level = kwargs.get('admin_level')
        language_de = get_datatables_language_de_from_locale(request)

        context = {
            'tally_id': tally_id,
            "admin_level": admin_level,
            'languageDE': language_de,
            "remote_url":
                reverse(
                    'turnout-report-by-gender-data',
                    kwargs=kwargs
                ),
            }

        return render(
            request,
            'reports/turnout_report_by_gender_and_admin_area.html',
            context
        )
