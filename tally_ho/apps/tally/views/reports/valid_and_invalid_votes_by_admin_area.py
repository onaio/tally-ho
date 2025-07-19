from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models import ReconciliationForm, Result, ResultForm
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.reports.list_base_data_view import NoneQsBaseDataView
from tally_ho.libs.views.mixins import (DataTablesMixin, GroupRequiredMixin,
                                        TallyAccessMixin)


def valid_votes_query(
        tally_id,
        admin_level_filter_name,
        admin_area_name,
        sub_race_type,
    ):
    """
    Get the valid votes from the result form
    :param tally_id: The id of the tally
    :param admin_level_filter_name: The name of the admin level filter
    :param admin_area_name: The name of the admin area
    :param sub_race_type: The sub race type
    :return: The valid votes from the result form
    """
    area_filter_map =\
                {
                    f"result_form__{admin_level_filter_name}":
                    admin_area_name
                }
    return Result.objects.filter(
            result_form__tally__id=tally_id,
            **area_filter_map,
            result_form__form_state=FormState.ARCHIVED,
            entry_version=EntryVersion.FINAL,
            result_form__ballot__electrol_race__ballot_name=\
                sub_race_type,
            active=True,
    ).aggregate(
        valid_votes=Coalesce(Sum('votes'), 0)
    ).get('valid_votes')

def invalid_votes_query(
        tally_id,
        admin_level_filter_name,
        admin_area_name,
        sub_race_type,
    ):
    """
    Get the invalid votes from the reconciliation form
    :param tally_id: The id of the tally
    :param admin_level_filter_name: The name of the admin level filter
    :param admin_area_name: The name of the admin area
    :param sub_race_type: The sub race type
    :return: The invalid votes from the reconciliation form
    """
    area_filter_map =\
                {
                    f"result_form__{admin_level_filter_name}":
                    admin_area_name
                }
    return  ReconciliationForm.objects.filter(
            result_form__tally__id=tally_id,
            **area_filter_map,
            result_form__form_state=FormState.ARCHIVED,
            entry_version=EntryVersion.FINAL,
            result_form__ballot__electrol_race__ballot_name=\
                sub_race_type,
            active=True,
    ).aggregate(
        invalid_votes=Coalesce(Sum('number_invalid_votes'), 0)
    ).get('invalid_votes')

def get_valid_and_invalid_votes_by_admin_area(
        tally_id,
        admin_level_filter_name,
        admin_level_filter_value,
    ):
    """
    Get the invalid votes from the result form
    :param tally_id: The id of the tally
    :param admin_level_filter_name: The name of the admin level filter
    :param center_code: The center code
    :param sub_race_type: The sub race type
    :param station_number: The station number
    :return: The invalid votes from the result form
    """
    base_query = ResultForm.objects.filter(
        tally__id=tally_id,
    )
    if admin_level_filter_value:
        area_filter_map =\
                {
                    f"{admin_level_filter_name}__icontains":
                    admin_level_filter_value
                }
        sub_race_filter_map =\
                {
                    "ballot__electrol_race__ballot_name__icontains":
                    admin_level_filter_value
                }
        base_query = base_query.filter(
            Q(**area_filter_map) |
            Q(**sub_race_filter_map)
        )
    return base_query.annotate(
        sub_race_type=F('ballot__electrol_race__ballot_name'),
        admin_area_name=F(admin_level_filter_name),
    ).values(
        'admin_area_name',
        'sub_race_type',
    ).distinct()

class ValidAndInvalidVotesByAdminAreasDataView(
    LoginRequiredMixin, GroupRequiredMixin, TallyAccessMixin,
    NoneQsBaseDataView
    ):
    group_required = groups.TALLY_MANAGER
    columns = (
        "admin_area_name",
        "sub_race",
        "total_valid_votes",
        "total_invalid_votes",
    )

    def get_initial_queryset(self):
        tally_id = self.kwargs.get('tally_id')
        admin_level = self.kwargs.get('admin_level')
        admin_level_filter_name = None
        admin_level_filter_value = self.request.POST.get('search[value]')
        if admin_level == "office":
            admin_level_filter_name = 'office__name'
        elif admin_level == "constituency":
            admin_level_filter_name = 'center__constituency__name'
        elif admin_level == "sub_constituency":
            admin_level_filter_name = 'center__sub_constituency__name'
        else:
            admin_level_filter_name = 'office__region__name'

        ret_value = []

        for valid_votes_by_sub_race_type in\
            get_valid_and_invalid_votes_by_admin_area(
                tally_id,
                admin_level_filter_name,
                admin_level_filter_value,
            ):
            response = {}
            response['admin_area_name'] =\
                valid_votes_by_sub_race_type.get('admin_area_name')
            response['sub_race'] =\
                valid_votes_by_sub_race_type.get('sub_race_type')
            response['total_valid_votes'] = valid_votes_query(
                tally_id=tally_id,
                admin_level_filter_name=admin_level_filter_name,
                admin_area_name=\
                    valid_votes_by_sub_race_type.get('admin_area_name'),
                sub_race_type=\
                    valid_votes_by_sub_race_type.get('sub_race_type'),
            )
            response['total_invalid_votes'] = invalid_votes_query(
                tally_id=tally_id,
                admin_level_filter_name=admin_level_filter_name,
                admin_area_name=\
                    valid_votes_by_sub_race_type.get('admin_area_name'),
                sub_race_type=\
                    valid_votes_by_sub_race_type.get('sub_race_type'),
            )
            ret_value.append(response)

        return self.ordering(ret_value)

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
                ValidAndInvalidVotesByAdminAreasDataView, self
                ).render_column(row, column)

def get_aggregate_data(data):
    aggregate = {}
    aggregate['admin_area_name'] = "Total"
    aggregate["sub_race"] = ""
    aggregate["total_valid_votes"] = sum(
        entry['total_valid_votes'] for entry in
        data
        )
    aggregate["total_invalid_votes"] = sum(
        entry['total_invalid_votes'] for entry in
        data
        )
    return aggregate

class ValidAndInvalidVotesByAdminAreasView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    DataTablesMixin,
    TemplateView
    ):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/valid_and_invalid_votes_by_admin_area.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        admin_level = kwargs.get('admin_level')

        context = {
            'tally_id': tally_id,
            "admin_level": admin_level,
            "remote_url":
                reverse(
                    'valid-and-invalid-votes-by-adminarea-data',
                    kwargs=kwargs
                ),
            "regions_turnout_report_url": reverse(
                "turnout-list",
                kwargs={"tally_id": tally_id, "admin_level": "region"},
            ),
            "offices_remote_url": reverse(
                "turnout-list",
                kwargs={"tally_id": tally_id, "admin_level": "office"},
            ),
            "export_file_name": "valid-and-invalid-votes-by-admin-area",
            }

        return self.render_to_response(self.get_context_data(**context))
