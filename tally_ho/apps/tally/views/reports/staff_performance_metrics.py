from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from django.db.models import Count, Q, Sum, F, ExpressionWrapper,\
    IntegerField, Value as V
from django.db.models.functions import Coalesce
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


def approvals_percantage(
    approvals, decimal_digits=2, default_percentage_value=0
):
    """Calculates supervisor's approvals rate percentage value.

    :param approvals: A dict consisting of forms processed by supervisor
        and forms sent for review by supervisor.
    :param decimal_digits: The number of digits to round off the percentage
        value, default is two.
    :param default_percentage_value: The default percentage value returned
        when forms_sent_for_review is not True

    :returns: Percentage float value rounded in two dencimal points
        if forms sent for review is greater than zero,
        Zero if forms sent for review is not greater than zero.
    """
    forms_approved = approvals['forms_approved']
    forms_sent_for_review = approvals['forms_sent_for_review']

    if forms_sent_for_review:
        return round(
            100 * forms_approved/forms_sent_for_review, decimal_digits)
    return default_percentage_value


class StaffPerformanceMetricsView(LoginRequiredMixin,
                                  mixins.GroupRequiredMixin,
                                  TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/staff_performance_metrics.html'

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        group_name = kwargs['group_name']

        result_form_stats =\
            ResultFormStats.objects\
            .filter(
                result_form__tally__id=tally_id,
                user__groups__name=group_name)\
            .values('user__username')\
            .annotate(
                forms_processed=Count('user'),
                total_processing_time=Coalesce(Sum('processing_time'), V(0)))

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                result_form_stats=result_form_stats,
                user_group=group_name))


class SupervisorsApprovalsView(LoginRequiredMixin,
                               mixins.GroupRequiredMixin,
                               TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/supervisor_approvals.html'

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']

        tally_result_forms_stats =\
            ResultFormStats.objects.filter(
                user__groups__name__in=[groups.AUDIT_SUPERVISOR,
                                        groups.SUPER_ADMINISTRATOR,
                                        groups.TALLY_MANAGER],
                result_form__tally__id=tally_id,
                reviewed_by_supervisor=True)

        result_forms_stats = tally_result_forms_stats\
            .annotate(
                count_approved_by_tally_manager=Count(
                    'approved_by_supervisor',
                    filter=Q(user__groups__name=groups.TALLY_MANAGER,
                             approved_by_supervisor=True)))\
            .annotate(
                count_sent_for_review_by_tally_manager=Count(
                    'id',
                    filter=Q(user__groups__name=groups.TALLY_MANAGER)))\
            .annotate(
                count_approved_by_supervisor_admin=Count(
                    'approved_by_supervisor',
                    filter=Q(user__groups__name=groups.SUPER_ADMINISTRATOR,
                             approved_by_supervisor=True)))\
            .annotate(
                count_sent_for_review_by_supervisor_admin=Count(
                    'id',
                    filter=Q(user__groups__name=groups.SUPER_ADMINISTRATOR)))\
            .annotate(
                count_approved_by_audit_supervisor=Count(
                    'approved_by_supervisor',
                    filter=Q(user__groups__name=groups.AUDIT_SUPERVISOR,
                             approved_by_supervisor=True)))\
            .annotate(
                count_sent_for_review_by_audit_supervisor=Count(
                    'id',
                    filter=Q(user__groups__name=groups.AUDIT_SUPERVISOR)))\
            .aggregate(
                approved_by_tally_manager=Sum(
                    'count_approved_by_tally_manager'),
                sent_for_review_by_tally_manager=Sum(
                    'count_sent_for_review_by_tally_manager'),
                approved_by_supervisor_admin=Sum(
                    'count_approved_by_supervisor_admin'),
                sent_for_review_by_supervisor_admin=Sum(
                    'count_sent_for_review_by_supervisor_admin'),
                approved_by_audit_supervisor=Sum(
                    'count_approved_by_audit_supervisor'),
                sent_for_review_by_audit_supervisor=Sum(
                    'count_sent_for_review_by_audit_supervisor'))

        tally_manager_supervisor_approvals =\
            {'forms_approved':
             result_forms_stats['approved_by_tally_manager'],
             'forms_sent_for_review':
             result_forms_stats['sent_for_review_by_tally_manager']}

        supervisor_administrator_approvals =\
            {'forms_approved':
             result_forms_stats['approved_by_supervisor_admin'],
             'forms_sent_for_review':
             result_forms_stats['sent_for_review_by_supervisor_admin']}

        audit_supervisor_approvals =\
            {'forms_approved':
             result_forms_stats['approved_by_audit_supervisor'],
             'forms_sent_for_review':
             result_forms_stats['sent_for_review_by_audit_supervisor']}
        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                t_m_approvals=tally_manager_supervisor_approvals,
                t_m_approvals_percantage=approvals_percantage(
                    tally_manager_supervisor_approvals),
                s_a_approvals=supervisor_administrator_approvals,
                s_a_approvals_percantage=approvals_percantage(
                    supervisor_administrator_approvals),
                a_s_approvals=audit_supervisor_approvals,
                a_s_approvals_percantage=approvals_percantage(
                    audit_supervisor_approvals)))


class TrackCorrections(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/corrections_statistics.html'

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        corrections_stats = None
        percentage_value = 100

        qs =\
            ResultFormStats.objects\
            .filter(
                user__groups__name__in=[groups.DATA_ENTRY_1_CLERK,
                                        groups.DATA_ENTRY_2_CLERK],
                result_form__tally__id=tally_id)

        if qs:
            corrections_stats =\
                qs.values('user__username')\
                .annotate(
                    total_forms_processed=Count('user'),
                    total_errors=Count(
                        'data_entry_errors',
                        filter=Q(data_entry_errors__gt=0)))\
                .annotate(
                    error_percentage=ExpressionWrapper(
                        V(percentage_value) *
                        F('total_errors')
                        / F('total_forms_processed'),
                        output_field=IntegerField()
                    ))\
                .order_by('-error_percentage')

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                corrections_stats=corrections_stats))
