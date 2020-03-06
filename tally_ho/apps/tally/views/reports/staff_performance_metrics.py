from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from django.db.models import Count, Q, Sum
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class StaffPerformanceMetricsView(LoginRequiredMixin,
                                  mixins.GroupRequiredMixin,
                                  TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/staff_performance_metrics.html'

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        group_name = kwargs['group_name']
        tally_result_forms = ResultFormStats.objects.filter(
            result_form__tally__id=tally_id)
        result_form_stats =\
            [result_form for result_form in tally_result_forms
                if groups.user_groups(result_form.user)[0] == group_name]

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                result_form_stats=result_form_stats,
                result_forms_count=len(result_form_stats),
                user_group=group_name))


class SupervisorsApprovalsView(LoginRequiredMixin,
                               mixins.GroupRequiredMixin,
                               TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/supervisor_approvals.html'

    def approvals_percantage(self, approvals):
        """Calculates supervisor's approvals rate percentage value.

        :param approvals: A dict consisting of forms processed by supervisor
            and forms sent for review by supervisor.

        :returns: Percentage float value rounded in two dencimal points
            if forms sent for review is greater than zero,
            Zero if forms sent for review is not greater than zero.
        """
        forms_approved = approvals['forms_approved']
        forms_sent_for_review = approvals['forms_sent_for_review']

        if forms_sent_for_review > 0:
            return round(100 * forms_approved/forms_sent_for_review, 2)
        return 0

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']

        tally_result_forms_stats =\
            ResultFormStats.objects.filter(
                user__groups__name__in=[groups.AUDIT_SUPERVISOR,
                                        groups.SUPER_ADMINISTRATOR,
                                        groups.TALLY_MANAGER],
                result_form__tally__id=tally_id,
                reviewed_by_supervisor=True)

        qs = tally_result_forms_stats\
            .annotate(
                count_approved_by_tally_manager=Count(
                    'approved_by_supervisor',
                    filter=Q(user__groups__name=groups.TALLY_MANAGER,
                             approved_by_supervisor=True)))\
            .annotate(
                count_sent_for_review_by_tally_manager=Count(
                    'sent_for_review',
                    filter=Q(user__groups__name=groups.TALLY_MANAGER,
                             sent_for_review=True)))\
            .annotate(
                count_approved_by_supervisor_admin=Count(
                    'approved_by_supervisor',
                    filter=Q(user__groups__name=groups.SUPER_ADMINISTRATOR,
                             approved_by_supervisor=True)))\
            .annotate(
                count_sent_for_review_by_supervisor_admin=Count(
                    'sent_for_review',
                    filter=Q(user__groups__name=groups.SUPER_ADMINISTRATOR,
                             sent_for_review=True)))\
            .annotate(
                count_approved_by_audit_supervisor=Count(
                    'approved_by_supervisor',
                    filter=Q(user__groups__name=groups.AUDIT_SUPERVISOR,
                             approved_by_supervisor=True)))\
            .annotate(
                count_sent_for_review_by_audit_supervisor=Count(
                    'sent_for_review',
                    filter=Q(user__groups__name=groups.AUDIT_SUPERVISOR,
                             sent_for_review=True)))\
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
             qs['approved_by_tally_manager'],
             'forms_sent_for_review':
             qs['sent_for_review_by_tally_manager']}

        supervisor_administrator_approvals =\
            {'forms_approved':
             qs['approved_by_supervisor_admin'],
             'forms_sent_for_review':
             qs['sent_for_review_by_supervisor_admin']}

        audit_supervisor_approvals =\
            {'forms_approved':
             qs['approved_by_audit_supervisor'],
             'forms_sent_for_review':
             qs['sent_for_review_by_audit_supervisor']}
        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                t_m_approvals=tally_manager_supervisor_approvals,
                t_m_approvals_percantage=self.approvals_percantage(
                    tally_manager_supervisor_approvals),
                s_a_approvals=supervisor_administrator_approvals,
                s_a_approvals_percantage=self.approvals_percantage(
                    supervisor_administrator_approvals),
                a_s_approvals=audit_supervisor_approvals,
                a_s_approvals_percantage=self.approvals_percantage(
                    audit_supervisor_approvals)))
