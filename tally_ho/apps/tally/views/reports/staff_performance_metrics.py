from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

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

    def update_forms_count(self, result_form_stat, approvals_type):
        """Update total forms approved and sent for review by supervisor.

        :param result_form_stat: The result form stat record.
        :param approvals_type: The user group approvals type.
        """
        if result_form_stat.approved_by_supervisor:
            approvals_type['forms_approved'] += 1

        if result_form_stat.sent_for_review:
            approvals_type['forms_sent_for_review'] += 1

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']

        tally_result_forms_stats = ResultFormStats.objects.filter(
            result_form__tally__id=tally_id,
            reviewed_by_supervisor=True)
        tally_manager_supervisor_approvals =\
            {'forms_approved': 0, 'forms_sent_for_review': 0}
        supervisor_administrator_approvals =\
            {'forms_approved': 0, 'forms_sent_for_review': 0}
        audit_supervisor_approvals =\
            {'forms_approved': 0, 'forms_sent_for_review': 0}

        for result_form_stat in tally_result_forms_stats:
            user_group_name = groups.user_groups(result_form_stat.user)[0]

            if user_group_name == groups.AUDIT_SUPERVISOR:
                self.update_forms_count(
                    result_form_stat,
                    audit_supervisor_approvals)
            if user_group_name == groups.SUPER_ADMINISTRATOR:
                self.update_forms_count(
                    result_form_stat,
                    supervisor_administrator_approvals)
            if user_group_name == groups.TALLY_MANAGER:
                self.update_forms_count(
                    result_form_stat,
                    tally_manager_supervisor_approvals)

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
