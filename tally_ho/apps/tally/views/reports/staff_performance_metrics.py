import string
from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.libs.models.enums.form_state import FormState
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
        form_state = kwargs['form_state']
        result_form_stats = ResultFormStats.objects.filter(
            result_form__tally__id=tally_id,
            form_state=form_state)
        user_group =\
            string.capwords(FormState(int(form_state)).name.replace("_", " "))
        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                result_form_stats=result_form_stats,
                user_group=user_group))
