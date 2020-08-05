from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _
from guardian.mixins import LoginRequiredMixin

from django.db.models import Count, Q, Sum, F, ExpressionWrapper,\
    IntegerField, Value as V
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.utils.templates import generate_csv_export

report_types = {1: "turnout", 2: "summary"}


def get_admin_areas_with_forms_in_audit(
        tally_id,
        report_column_name,
        report_column_id,
        region_id=None,
        constituency_id=None):
    """
    Genarate a report of stations and centers with result forms in audit state.

    :param tally_id: The reconciliation forms tally.
    :param report_column_name: The result form report column name.
    :param report_column_id: The result form report column id.
    :param region_id: The result form report region id used for filtering.
    :param constituency_id: The result form report constituency id
        used for filtering.

    returns: The stations and centers report grouped by the report column name.
    """
    qs =\
        ResultForm.objects.filter(
            tally__id=tally_id,
            form_state=FormState.AUDIT
        )
    if region_id:
        qs =\
            qs.filter(office__region__id=region_id)
    if constituency_id:
        qs =\
            qs.filter(center__constituency__id=constituency_id)
    qs =\
        qs.annotate(
            admin_area_name=F(report_column_name))\
        .annotate(
            region_id=F('office__region__id'))\
        .annotate(
            constituency_id=F('center__constituency__id'))\
        .annotate(
            sub_constituency_id=F('center__sub_constituency__id'))\
        .values(
            'admin_area_name',
            'region_id',
            'constituency_id',
            'sub_constituency_id'
        )\
        .annotate(
            number_of_centers_in_audit_state=Count('center'))\
        .annotate(
            number_of_stations_in_audit_state=Count('station_number'))\
        .annotate(
            total_num_of_centers_and_stations_in_audit=ExpressionWrapper(
                F('number_of_centers_in_audit_state') +
                F('number_of_stations_in_audit_state'),
                output_field=IntegerField()))

    return qs


def generate_report(
        tally_id,
        report_column_name,
        report_column_id,
        report_type_name,
        region_id=None,
        constituency_id=None):
    """
    Genarate report by using the final reconciliation form to get voter stats.

    :param tally_id: The reconciliation forms tally.
    :param report_column_name: The result form report column name.
    :param region_id: The region id for filtering the recon forms.
    :param constituency_id: The constituency id for filtering the recon forms.
    :param report_type_name: The report type name to generate.

    returns: The turnout report grouped by the report column name.
    """
    turnout_report_type_name = report_types[1]
    summary_report_type_name = report_types[2]
    turnout_report = None
    summary_report = None

    qs =\
        ReconciliationForm.objects.get_registrants_and_votes_type().filter(
            result_form__tally__id=tally_id,
            entry_version=EntryVersion.FINAL
        )
    if region_id:
        qs = qs.filter(result_form__office__region__id=region_id)

    if constituency_id:
        qs =\
            qs.filter(result_form__center__constituency__id=constituency_id)
    qs =\
        qs\
        .annotate(
            name=F(report_column_name))\
        .annotate(
            admin_area_id=F(report_column_id))\
        .annotate(
            constituency_id=F('result_form__center__constituency__id'))\
        .values(
            'name',
            'admin_area_id',
            'constituency_id'
        )

    if report_type_name == turnout_report_type_name:
        turnout_report =\
            qs\
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

    if report_type_name == summary_report_type_name:
        summary_report =\
            qs\
            .annotate(
                number_valid_votes=Sum('number_valid_votes'))\
            .annotate(
                number_invalid_votes=Sum('number_invalid_votes'))\
            .annotate(
                number_cancelled_ballots=Sum('number_cancelled_ballots'))

    return turnout_report or summary_report


class RegionsReportsView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/administrative_areas_reports.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs['tally_id']
        export_type_ = kwargs.get('export_type')
        report_type_ = kwargs.get('report_type')
        region_id = kwargs.get('region_id')

        column_name = 'result_form__office__region__name'
        column_id = 'result_form__office__region__id'
        turnout_report = generate_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            report_type_name=report_types[1])
        summary_report = generate_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            report_type_name=report_types[2])
        regions_with_forms_in_audit = get_admin_areas_with_forms_in_audit(
            tally_id=tally_id,
            report_column_name='office__region__name',
            report_column_id='office__region__id')

        if report_type_ == 'centers-and-stations-in-audit-report':
            self.request.session['station_ids'] =\
                list(regions_with_forms_in_audit.values_list(
                    'station_number', flat=True))

            return redirect(
                'center-and-stations-in-audit-list',
                tally_id=tally_id,
                region_id=region_id)

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
                report_name=_(u'Region'),
                turn_out_report_download_url='regions-turnout-csv',
                summary_report_download_url='regions-summary-csv',
                turnout_report=turnout_report,
                summary_report=summary_report,
                admin_ares_with_forms_in_audit=regions_with_forms_in_audit,
                regions_report_url='regions-discrepancy-report',
                child_turnout_report_url='constituency-turnout-report',
                child_summary_report_url='constituency-summary-report'))


class ConstituencyReportsView(LoginRequiredMixin,
                              mixins.GroupRequiredMixin,
                              TemplateView):
    group_required = groups.TALLY_MANAGER

    def get(self, request, *args, **kwargs):
        tally_id = kwargs['tally_id']
        region_id = kwargs['region_id']
        report_type = kwargs.get('report_type', None)
        constituency_id = kwargs.get('constituency_id', None)

        region_name =\
            Region.objects.get(
                id=region_id, tally__id=tally_id).name if region_id else None
        export_type_ = kwargs.get('export_type')
        column_name = 'result_form__center__constituency__name'
        column_id = 'result_form__center__constituency__id'
        turnout_report = generate_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            report_type_name=report_types[1],
            region_id=region_id)
        summary_report = generate_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            report_type_name=report_types[2],
            region_id=region_id)

        if report_type == 'centers-and-stations-in-audit-report':
            self.request.session['station_ids'] =\
                list(constituencies_forms_in_audit.values_list(
                    'station_number', flat=True))

            return redirect(
                'center-and-stations-in-audit-list',
                tally_id=tally_id,
                region_id=region_id,
                constituency_id=constituency_id)

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
                region_id=region_id,
                administrative_area_name=_(u'Constituencies'),
                administrative_area_child_report_name=_(u'Sub Constituencies'),
                turn_out_report_download_url='constituencies-turnout-csv',
                summary_report_download_url='constituencies-summary-csv',
                turnout_report=turnout_report,
                summary_report=summary_report,
                region_name=region_name,
                child_turnout_report_url='sub-constituency-turnout-report',
                child_summary_report_url='sub-constituency-summary-report'))


class SubConstituencyReportsView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 TemplateView):
    group_required = groups.TALLY_MANAGER

    def get(self, request, *args, **kwargs):
        export_type_ = kwargs.get('export_type')
        tally_id = kwargs['tally_id']
        region_id = kwargs['region_id']
        constituency_id = kwargs['constituency_id']

        region_name =\
            Region.objects.get(
                id=region_id, tally__id=tally_id).name if region_id else None
        constituency_name =\
            Constituency.objects.get(
                id=constituency_id,
                tally__id=tally_id).name if constituency_id else None

        column_name = 'result_form__center__sub_constituency__code'
        column_id = 'result_form__center__sub_constituency__id'
        turnout_report = generate_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            report_type_name=report_types[1],
            region_id=region_id,
            constituency_id=constituency_id)
        summary_report = generate_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            report_type_name=report_types[2],
            region_id=region_id,
            constituency_id=constituency_id)

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
                region_id=region_id,
                constituency_id=constituency_id,
                turn_out_report_download_url="sub-constituencies-turnout-csv",
                summary_report_download_url="sub-constituencies-summary-csv",
                turnout_report=turnout_report,
                summary_report=summary_report,
                administrative_area_name=_(u"Sub Constituencies"),
                region_name=region_name,
                constituency_name=constituency_name))
