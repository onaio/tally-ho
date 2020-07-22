from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _
from guardian.mixins import LoginRequiredMixin

from django.db.models import Q, Sum, F, ExpressionWrapper, IntegerField,\
    Value as V
from django.db.models.functions import Coalesce
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.utils.templates import generate_csv_export


def generate_voters_turnout_report(tally_id, report_column_name):
    """
    Genarate voters turnout report by using the final reconciliation
    form to get voter stats.

    :param tally_id: The reconciliation forms tally.
    :param report_column_name: The result form report column name.

    returns: The turnout report grouped by the report column name.
    """
    turnout_report =\
        ReconciliationForm.objects.get_registrants_and_votes_type().filter(
            result_form__tally__id=tally_id,
            entry_version=EntryVersion.FINAL
        )\
        .annotate(
            name=F(report_column_name))\
        .values(
            'name'
        )\
        .annotate(
            number_of_voters_voted=Sum('number_valid_votes'))\
        .annotate(
            total_number_of_registrants=Sum('number_of_registrants'))\
        .annotate(
            total_number_of_ballots_used=Sum(
                ExpressionWrapper(F('number_valid_votes') +
                                  F('number_cancelled_ballots') +
                                  F('number_unstamped_ballots') +
                                  F('number_invalid_votes'),
                                  output_field=IntegerField())))\
        .annotate(turnout_percentage=ExpressionWrapper(
            V(100) *
            F('total_number_of_ballots_used') /
            F('total_number_of_registrants'),
            output_field=IntegerField()))\
        .annotate(male_voters=Coalesce(
            Sum('number_valid_votes',
                filter=Q(voters_gender_type=0)),
            V(0)))\
        .annotate(female_voters=Coalesce(
            Sum('number_valid_votes',
                filter=Q(voters_gender_type=1)),
            V(0)))

    return turnout_report


def generate_votes_summary_report(tally_id, adminstrative_area_col_name):
    """
    Genarate votes summary report per adminstrative
    area (region, constituency etc.).

    :param tally_id: The reconciliation forms tally.
    :param adminstrative_area_col_name: The result form adminstrative area
    column name.

    returns: The votes summary report grouped by the adminstrative area
    column name.
    """
    summary_report =\
        ReconciliationForm.objects.get_registrants_and_votes_type().filter(
            result_form__tally__id=tally_id,
            entry_version=EntryVersion.FINAL
        )\
        .annotate(
            name=F(adminstrative_area_col_name))\
        .values(
            'name'
        )\
        .annotate(
            number_valid_votes=Sum('number_valid_votes'))\
        .annotate(
            number_invalid_votes=Sum('number_invalid_votes'))\
        .annotate(
            number_cancelled_ballots=Sum('number_cancelled_ballots'))

    return summary_report


class RegionsReportsView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/administrative_areas_reports.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs['tally_id']
        export_type_ = kwargs.get('export_type')
        column_name = 'result_form__office__region__name'
        turnout_report = generate_voters_turnout_report(
            tally_id,
            column_name)
        summary_report = generate_votes_summary_report(
            tally_id,
            column_name)

        if export_type_ == 'turnout-csv':
            header_map = {
                'name': 'region name',
                'total_number_of_registrants': 'total number of voters',
                'number_of_voters_voted': 'number of voters voted',
                'male_voters': 'male voters',
                'female_voters': 'female voters',
                'turnout_percentage': 'turnout percentage'
            }

            return generate_csv_export(
                report_query_set=turnout_report,
                filename='regions_turnout_report',
                header_map=header_map)

        if export_type_ == 'summary-csv':
            header_map = {
                'name': 'region name',
                'number_valid_votes': 'total number of valid votes',
                'number_invalid_votes': 'total number of invalid votes',
                'number_cancelled_ballots': 'total number of cancelled votes'
            }

            return generate_csv_export(
                report_query_set=summary_report,
                filename='regions_summary_report',
                header_map=header_map)

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                report_name=_(u"Region"),
                turn_out_report_download_url="regions-turnout-csv",
                summary_report_download_url="regions-summary-csv",
                turnout_report=turnout_report,
                summary_report=summary_report))


class ConstituencyReportsView(LoginRequiredMixin,
                              mixins.GroupRequiredMixin,
                              TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/administrative_areas_reports.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs['tally_id']
        export_type_ = kwargs.get('export_type')
        column_name = 'result_form__center__constituency__name'
        turnout_report = generate_voters_turnout_report(
            tally_id,
            column_name)
        summary_report = generate_votes_summary_report(
            tally_id,
            column_name)

        if export_type_ == 'turnout-csv':
            header_map = {
                'name': 'constituency name',
                'total_number_of_registrants': 'total number of voters',
                'number_of_voters_voted': 'number of voters voted',
                'male_voters': 'male voters',
                'female_voters': 'female voters',
                'turnout_percentage': 'turnout percentage'
            }

            return generate_csv_export(
                report_query_set=turnout_report,
                filename='constituencies_turnout_report',
                header_map=header_map)

        if export_type_ == 'summary-csv':
            header_map = {
                'name': 'constituency name',
                'number_valid_votes': 'total number of valid votes',
                'number_invalid_votes': 'total number of invalid votes',
                'number_cancelled_ballots': 'total number of cancelled votes'
            }

            return generate_csv_export(
                report_query_set=summary_report,
                filename='constituencies_summary_report',
                header_map=header_map)

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                report_name=_(u"Constituency"),
                turn_out_report_download_url="constituencies-turnout-csv",
                summary_report_download_url="constituencies-summary-csv",
                turnout_report=turnout_report,
                summary_report=summary_report))


class SubConstituencyReportsView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/administrative_areas_reports.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs['tally_id']
        export_type_ = kwargs.get('export_type')
        column_name = 'result_form__center__sub_constituency__code'
        turnout_report = generate_voters_turnout_report(
            tally_id,
            column_name)
        summary_report = generate_votes_summary_report(
            tally_id,
            column_name)

        if export_type_ == 'turnout-csv':
            header_map = {
                'name': 'subconstituency name',
                'total_number_of_registrants': 'total number of voters',
                'number_of_voters_voted': 'number of voters voted',
                'male_voters': 'male voters',
                'female_voters': 'female voters',
                'turnout_percentage': 'turnout percentage'
            }

            return generate_csv_export(
                report_query_set=turnout_report,
                filename='sub_constituencies_turnout_report',
                header_map=header_map)

        if export_type_ == 'summary-csv':
            header_map = {
                'name': 'subconstituency name',
                'number_valid_votes': 'total number of valid votes',
                'number_invalid_votes': 'total number of invalid votes',
                'number_cancelled_ballots': 'total number of cancelled votes'
            }

            return generate_csv_export(
                report_query_set=summary_report,
                filename='sub_constituencies_summary_report',
                header_map=header_map)

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                turn_out_report_download_url="sub-constituencies-turnout-csv",
                summary_report_download_url="sub-constituencies-summary-csv",
                turnout_report=turnout_report,
                summary_report=summary_report,
                report_name=_(u"Sub Constituency")))
