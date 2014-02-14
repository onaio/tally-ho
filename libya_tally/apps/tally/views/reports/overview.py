from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from libya_tally.libs.permissions import groups
from libya_tally.libs.reports import progress as p
from libya_tally.libs.views import mixins


class OverviewReportView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'tally/reports/overview.html'

    def get(self, *args, **kwargs):
        overviews = [
            p.ExpectedProgressReport(),
            p.IntakenProgressReport,
            p.ArchivedProgressReport,
            p.ClearanceProgressReport,
            p.AuditProgressReport,
            p.NotRecievedProgressReport
        ]

        return self.render_to_response(
            self.get_context_data(overviews=overviews))
