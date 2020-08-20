from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _
from guardian.mixins import LoginRequiredMixin

from django.db.models import Count, Q, Sum, F, ExpressionWrapper,\
    IntegerField, Value as V, Subquery, OuterRef
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState

report_types = {1: "turnout",
                2: "summary",
                3: "stations_centers_under_investigation",
                4: "stations_centers_excluded_after_investigation"}


def get_stations_and_centers_by_admin_area(
        tally_id,
        report_column_name,
        report_column_id,
        report_type_name,
        region_id=None,
        constituency_id=None):
    """
    Genarate a report of stations and centers under investigation or excluded
    after investigation.

    :param tally_id: The reconciliation forms tally.
    :param report_column_name: The result form report column name.
    :param report_column_id: The result form report column id.
    :param report_type_name: The report type name to generate.
    :param region_id: The result form report region id used for filtering.
    :param constituency_id: The result form report constituency id
        used for filtering.

    returns: The stations and centers report grouped by the adminstrative
        area name.
    """
    qs =\
        Station.objects.filter(tally__id=tally_id)

    stations_centers_under_investigation_report_type_name =\
        report_types[3]
    stations_centers_excluded_after_investigation_report_type_name =\
        report_types[4]

    if report_type_name ==\
            stations_centers_under_investigation_report_type_name:
        qs =\
            qs.filter(active=False)

    if report_type_name ==\
            stations_centers_excluded_after_investigation_report_type_name:
        qs =\
            qs.filter(
                Q(active=True,
                  center__disable_reason__isnull=False) |
                Q(active=True,
                  disable_reason__isnull=False))

    if region_id:
        qs =\
            qs.filter(center__office__region__id=region_id)
    if constituency_id:
        qs =\
            qs.filter(center__constituency__id=constituency_id)

    qs =\
        qs.annotate(
            admin_area_name=F(report_column_name),
            region_id=F('center__office__region__id'),)\
        .values(
            'admin_area_name',
            'region_id',
        )\
        .annotate(
            number_of_centers=Count('center'),
            number_of_stations=Count('station_number'),
            total_number_of_centers_and_stations=ExpressionWrapper(
                F('number_of_centers') +
                F('number_of_stations'),
                output_field=IntegerField()))

    if region_id:
        qs =\
            qs.annotate(
                constituency_id=F(
                    'center__constituency__id'),
                sub_constituency__id=F(
                    'sub_constituency__id'),
            )

    return qs


def generate_progressive_report(
        tally_id,
        report_column_name,
        report_column_id,
        region_id=None,
        constituency_id=None):
    """
    Genarate progressive report of candidates by votes.

    :param tally_id: The result form tally.
    :param report_column_name: The result form report column name.
    :param report_column_id: The result form report column id.
    :param region_id: The result form region id.
    :param constituency_id: The result form constituency id.

    returns: The candidates votes stats based on an administrative area.
    """
    qs =\
        Result.objects.filter(
            result_form__tally__id=tally_id,
            result_form__form_state=FormState.ARCHIVED,
            entry_version=EntryVersion.FINAL,
            active=True
        )

    if region_id:
        qs = qs.filter(result_form__office__region__id=region_id)

    if constituency_id:
        qs =\
            qs.filter(result_form__center__constituency__id=constituency_id)

    qs =\
        qs\
        .annotate(
            name=F(report_column_name),
            admin_area_id=F('result_form__office__region__id'))\
        .values(
            'name',
            'admin_area_id',
        )\
        .annotate(
            total_candidates=Count('candidate__id', distinct=True),
            total_votes=Sum('votes'))

    if region_id:
        qs =\
            qs.annotate(
                constituency_id=F(
                    'result_form__center__constituency__id'),
                sub_constituency_id=F(
                    'result_form__center__sub_constituency__id'),
            )

    return qs


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
            admin_area_name=F(report_column_name),
            region_id=F('office__region__id'))\
        .values(
            'admin_area_name',
            'region_id',
        )\
        .annotate(
            number_of_centers_in_audit_state=Count('center'),
            number_of_stations_in_audit_state=Count('station_number'),
            total_num_of_centers_and_stations_in_audit=ExpressionWrapper(
                F('number_of_centers_in_audit_state') +
                F('number_of_stations_in_audit_state'),
                output_field=IntegerField()))

    if region_id:
        qs =\
            qs.annotate(
                constituency_id=F('center__constituency__id'),
                sub_constituency_id=F('center__sub_constituency__id'),
            )

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
    :param report_column_id: The result form report column id.
    :param region_id: The region id for filtering the recon forms.
    :param constituency_id: The constituency id for filtering the recon forms.
    :param report_type_name: The report type name to generate.

    returns: The turnout report grouped by the report column name.
    """
    turnout_report_type_name = report_types[1]
    summary_report_type_name = report_types[2]

    qs =\
        ReconciliationForm.objects.get_registrants_and_votes_type().filter(
            result_form__tally__id=tally_id,
            result_form__form_state=FormState.ARCHIVED,
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
            name=F(report_column_name),
            admin_area_id=F(report_column_id))\
        .values(
            'name',
            'admin_area_id',
        )

    if region_id:
        qs =\
            qs.annotate(
                constituency_id=F('result_form__center__constituency__id'),
            )

    if report_type_name == turnout_report_type_name:
        qs =\
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
        qs =\
            qs\
            .annotate(
                number_valid_votes=Sum('number_valid_votes'))\
            .annotate(
                number_invalid_votes=Sum('number_invalid_votes'))\
            .annotate(
                number_cancelled_ballots=Sum('number_cancelled_ballots'))

    return qs


class RegionsReportsView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/administrative_areas_reports.html'

    def get(self, request, *args, **kwargs):
        tally_id = kwargs['tally_id']
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

        progressive_report = generate_progressive_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id)

        regions_with_forms_in_audit = get_admin_areas_with_forms_in_audit(
            tally_id=tally_id,
            report_column_name='office__region__name',
            report_column_id='office__region__id')

        centers_stations_under_invg =\
            get_stations_and_centers_by_admin_area(
                tally_id=tally_id,
                report_column_name='center__office__region__name',
                report_column_id='center__office__region__id',
                report_type_name=report_types[3])
        centers_stations_ex_after_invg =\
            get_stations_and_centers_by_admin_area(
                tally_id=tally_id,
                report_column_name='center__office__region__name',
                report_column_id='center__office__region__id',
                report_type_name=report_types[4])

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

        if report_type_ in\
            ['centers-and-stations-in-audit-report',
             'centers-and-stations-under-investigation',
             'centers-and-stations-excluded-after-investigation']:

            if report_type_ == 'centers-and-stations-in-audit-report':
                self.request.session['station_ids'] =\
                    list(regions_with_forms_in_audit.filter(
                        office__region__id=region_id)
                    .annotate(
                        station_id=station_id_query)
                    .values_list('station_id', flat=True))

            if report_type_ == 'centers-and-stations-under-investigation':
                self.request.session['station_ids'] =\
                    list(centers_stations_under_invg.filter(
                        center__office__region__id=region_id)
                    .annotate(
                        station_id=station_id_query)
                    .values_list('station_id', flat=True))

            if report_type_ ==\
                    'centers-and-stations-excluded-after-investigation':
                self.request.session['station_ids'] =\
                    list(centers_stations_ex_after_invg.filter(
                        center__office__region__id=region_id)
                    .annotate(
                        station_id=station_id_query)
                    .values_list('station_id', flat=True))

            return redirect(
                'center-and-stations-list',
                tally_id=tally_id,
                region_id=region_id)

        if report_type_ == 'votes-per-candidate-report':
            self.request.session['result_ids'] =\
                list(progressive_report
                     .filter(
                         result_form__center__office__region__id=region_id)
                     .values_list(
                         'id', flat=True))
            self.request.session['ballot_report'] = False

            return redirect(
                'candidate-list-by-votes',
                tally_id=tally_id,
                region_id=region_id)

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                report_name=_(u'Region'),
                administrative_area_child_report_name=_(
                    u'Region Constituencies'),
                turn_out_report_download_url='regions-turnout-csv',
                summary_report_download_url='regions-summary-csv',
                turnout_report=turnout_report,
                summary_report=summary_report,
                progressive_report=progressive_report,
                admin_ares_with_forms_in_audit=regions_with_forms_in_audit,
                centers_stations_under_invg=centers_stations_under_invg,
                centers_stations_ex_after_invg=centers_stations_ex_after_invg,
                regions_report_url='regions-discrepancy-report',
                child_turnout_report_url='constituency-turnout-report',
                child_summary_report_url='constituency-summary-report',
                child_discrepancy_report_url=str(
                    'constituency-discrepancy-report'
                ),
                child_progressive_report_url=str(
                    'constituency-progressive-report'
                ),
                admin_area_votes_per_candidate_report_url=str(
                    'region-votes-per-candidate'
                )))


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
        progressive_report = generate_progressive_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            region_id=region_id)
        constituencies_forms_in_audit = get_admin_areas_with_forms_in_audit(
            tally_id=tally_id,
            report_column_name='center__constituency__name',
            report_column_id='center__constituency__id',
            region_id=region_id)

        centers_stations_under_invg =\
            get_stations_and_centers_by_admin_area(
                tally_id=tally_id,
                report_column_name='center__office__region__name',
                report_column_id='center__office__region__id',
                report_type_name=report_types[3],
                region_id=region_id)
        centers_stations_ex_after_invg =\
            get_stations_and_centers_by_admin_area(
                tally_id=tally_id,
                report_column_name='center__office__region__name',
                report_column_id='center__office__region__id',
                report_type_name=report_types[4],
                region_id=region_id)

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

        if report_type in\
            ['centers-and-stations-in-audit-report',
             'centers-and-stations-under-investigation',
             'centers-and-stations-excluded-after-investigation']:

            if report_type == 'centers-and-stations-in-audit-report':
                self.request.session['station_ids'] =\
                    list(constituencies_forms_in_audit.filter(
                        center__office__region__id=region_id,
                        center__constituency__id=constituency_id)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))\
                    if constituency_id else list(
                        constituencies_forms_in_audit.filter(
                            center__office__region__id=region_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))

            if report_type == 'centers-and-stations-under-investigation':
                self.request.session['station_ids'] =\
                    list(centers_stations_under_invg.filter(
                        center__office__region__id=region_id,
                        center__constituency__id=constituency_id)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))\
                    if constituency_id else list(
                        constituencies_forms_in_audit.filter(
                            center__office__region__id=region_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))

            if report_type ==\
                    'centers-and-stations-excluded-after-investigation':
                self.request.session['station_ids'] =\
                    list(centers_stations_ex_after_invg.filter(
                        center__office__region__id=region_id,
                        center__constituency__id=constituency_id)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))\
                    if constituency_id else list(
                        constituencies_forms_in_audit.filter(
                            center__office__region__id=region_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))

            return redirect(
                'center-and-stations-list',
                tally_id=tally_id,
                region_id=region_id,
                constituency_id=constituency_id)

        if report_type == 'votes-per-candidate-report':
            self.request.session['result_ids'] =\
                list(progressive_report
                     .filter(
                         result_form__center__office__region__id=region_id)
                     .values_list(
                         'id', flat=True))
            self.request.session['ballot_report'] = False

            return redirect(
                'candidate-list-by-votes',
                tally_id=tally_id,
                region_id=region_id,
                constituency_id=constituency_id)

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                region_id=region_id,
                administrative_area_name=_(u'Constituencies'),
                administrative_area_child_report_name=_(u'Sub Constituencies'),
                turn_out_report_download_url='constituencies-turnout-csv',
                summary_report_download_url='constituencies-summary-csv',
                progressive_report_download_url=str(
                    'constituencies-progressive-csv'
                ),
                discrepancy_report_download_url=str(
                    'constituencies-discrepancy-csv'
                ),
                turnout_report=turnout_report,
                summary_report=summary_report,
                progressive_report=progressive_report,
                process_discrepancy_report=constituencies_forms_in_audit,
                centers_stations_under_invg=centers_stations_under_invg,
                centers_stations_ex_after_invg=centers_stations_ex_after_invg,
                region_name=region_name,
                child_turnout_report_url='sub-constituency-turnout-report',
                child_summary_report_url='sub-constituency-summary-report',
                child_progressive_report_url=str(
                    'sub-constituency-progressive-report'
                ),
                admin_area_votes_per_candidate_report_url=str(
                    'constituency-votes-per-candidate'
                ),
                constituency_discrepancy_report_url=str(
                    'constituency-discrepancy-report'
                ),
                child_discrepancy_report_url=str(
                    'sub-constituency-discrepancy-report'
                ),
                child_admin_area_under_investigation_report_url=str(
                    'sub-constituencies-under-investigation-report'
                ),
                child_admin_area_excluded_after_investigation_report_url=str(
                    'sub-constituencies-excluded-after-investigation-report'
                )))


class SubConstituencyReportsView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 TemplateView):
    group_required = groups.TALLY_MANAGER

    def get(self, request, *args, **kwargs):
        tally_id = kwargs['tally_id']
        region_id = kwargs.get('region_id', None)
        constituency_id = kwargs.get('constituency_id', None)
        sub_constituency_id = kwargs.get('sub_constituency_id', None)
        report_type = kwargs.get('report_type', None)

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
        progressive_report = generate_progressive_report(
            tally_id=tally_id,
            report_column_name=column_name,
            report_column_id=column_id,
            region_id=region_id,
            constituency_id=constituency_id)
        sub_constituencies_forms_in_audit =\
            get_admin_areas_with_forms_in_audit(
                tally_id=tally_id,
                report_column_name='center__sub_constituency__name',
                report_column_id='center__sub_constituency__id',
                region_id=region_id,
                constituency_id=constituency_id)

        centers_stations_under_invg =\
            get_stations_and_centers_by_admin_area(
                tally_id=tally_id,
                report_column_name='center__office__region__name',
                report_column_id='center__office__region__id',
                report_type_name=report_types[3],
                region_id=region_id,
                constituency_id=constituency_id)
        centers_stations_ex_after_invg =\
            get_stations_and_centers_by_admin_area(
                tally_id=tally_id,
                report_column_name='center__office__region__name',
                report_column_id='center__office__region__id',
                report_type_name=report_types[4],
                region_id=region_id,
                constituency_id=constituency_id)

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

        if report_type in\
            ['centers-and-stations-in-audit-report',
             'centers-and-stations-under-investigation',
             'centers-and-stations-excluded-after-investigation']:

            if report_type == 'centers-and-stations-in-audit-report':
                self.request.session['station_ids'] =\
                    list(sub_constituencies_forms_in_audit.filter(
                        center__office__region__id=region_id,
                        center__constituency__id=constituency_id,
                        center__sub_constituency__id=sub_constituency_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))\
                    if constituency_id and sub_constituency_id else list(
                        sub_constituencies_forms_in_audit.filter(
                            center__office__region__id=region_id,
                            center__constituency__id=constituency_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))

            if report_type == 'centers-and-stations-under-investigation':
                self.request.session['station_ids'] =\
                    list(centers_stations_under_invg.filter(
                        center__office__region__id=region_id,
                        center__constituency__id=constituency_id,
                        center__sub_constituency__id=sub_constituency_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))\
                    if constituency_id and sub_constituency_id else list(
                        centers_stations_under_invg.filter(
                            center__office__region__id=region_id,
                            center__constituency__id=constituency_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))

            if report_type ==\
                    'centers-and-stations-excluded-after-investigation':
                self.request.session['station_ids'] =\
                    list(centers_stations_ex_after_invg.filter(
                        center__office__region__id=region_id,
                        center__constituency__id=constituency_id,
                        center__sub_constituency__id=sub_constituency_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))\
                    if constituency_id and sub_constituency_id else list(
                        centers_stations_ex_after_invg.filter(
                            center__office__region__id=region_id,
                            center__constituency__id=constituency_id,)
                    .annotate(
                        station_id=station_id_query)
                        .values_list('station_id', flat=True))

            return redirect(
                'center-and-stations-list',
                tally_id=tally_id,
                region_id=region_id,
                constituency_id=constituency_id,
                sub_constituency_id=sub_constituency_id)

        if report_type in\
                ['votes-per-candidate-report',
                 'candidate-list-sorted-by-ballots-number']:
            self.request.session['result_ids'] =\
                list(progressive_report
                     .filter(
                         result_form__center__office__region__id=region_id)
                     .values_list(
                         'id', flat=True))
            self.request.session['ballot_report'] =\
                report_type == 'candidate-list-sorted-by-ballots-number'

            return redirect(
                'candidate-list-by-votes',
                tally_id=tally_id,
                region_id=region_id,
                constituency_id=constituency_id,
                sub_constituency_id=sub_constituency_id)

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                region_id=region_id,
                administrative_area_child_report_name=None,
                constituency_id=constituency_id,
                turn_out_report_download_url="sub-constituencies-turnout-csv",
                summary_report_download_url="sub-constituencies-summary-csv",
                progressive_report_download_url=str(
                    'sub-constituencies-progressive-csv'
                ),
                admin_area_votes_per_candidate_report_url=str(
                    'sub-constituency-votes-per-candidate'
                ),
                discrepancy_report_download_url=str(
                    'sub-constituencies-discrepancy-csv'
                ),
                turnout_report=turnout_report,
                summary_report=summary_report,
                progressive_report=progressive_report,
                process_discrepancy_report=sub_constituencies_forms_in_audit,
                centers_stations_under_invg=centers_stations_under_invg,
                centers_stations_ex_after_invg=centers_stations_ex_after_invg,
                administrative_area_name=_(u"Sub Constituencies"),
                region_name=region_name,
                constituency_name=constituency_name,
                sub_constituency_discrepancy_report_url=str(
                    'sub-constituency-discrepancy-report'
                ),))
