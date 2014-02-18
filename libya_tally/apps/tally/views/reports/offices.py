from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.models.office import Office
from libya_tally.libs.permissions import groups
from libya_tally.libs.reports import progress as p
from libya_tally.libs.views import mixins


class OfficesReportView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'tally/reports/offices.html'

    def get_per_office_progress(self):
        data = []

        for office in Office.objects.all():
            intaken = p.IntakenProgressReport().for_center_office(office)
            not_intaken = p.NotRecievedProgressReport()\
                .for_center_office(office)
            archived = p.ArchivedProgressReport().for_center_office(office)
            data.append({
                'office': office,
                'intaken': intaken.number,
                'not_intaken': not_intaken.number,
                'archived': archived.number,
            })
        return data

    def get(self, *args, **kwargs):
        overviews = [
            p.ExpectedProgressReport(),
            p.IntakenProgressReport(),
            p.ArchivedProgressReport(),
            p.ClearanceProgressReport(),
            p.AuditProgressReport(),
            p.NotRecievedProgressReport()
        ]

        return self.render_to_response(
            self.get_context_data(
                overviews=overviews,
                per_office=self.get_per_office_progress()))
