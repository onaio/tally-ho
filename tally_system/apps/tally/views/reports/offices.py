from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_system.apps.tally.models.office import Office
from tally_system.libs.permissions import groups
from tally_system.libs.reports import progress as p
from tally_system.libs.views import mixins


class OfficesReportView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'reports/offices.html'

    def get_per_office_progress(self):
        data = []

        for office in Office.objects.all().order_by('number'):
            intaken = p.IntakenProgressReport().for_center_office(office)
            not_intaken = p.NotRecievedProgressReport().for_center_office(
                office)
            archived = p.ArchivedProgressReport().for_center_office(office)
            data.append({
                'office': office,
                'number': office.number,
                'intaken': intaken.number,
                'not_intaken': not_intaken.number,
                'archived': archived.number,
            })

        return data

    def get(self, *args, **kwargs):
        overviews = [
            p.ExpectedProgressReport(),
            p.IntakenProgressReport(),
            p.DataEntry1ProgressReport(),
            p.DataEntry2ProgressReport(),
            p.CorrectionProgressReport(),
            p.QualityControlProgressReport(),
            p.ArchivingProgressReport(),
            p.ArchivedProgressReport(),
            p.ClearanceProgressReport(),
            p.AuditProgressReport(),
            p.NotRecievedProgressReport()
        ]

        return self.render_to_response(
            self.get_context_data(
                overviews=overviews,
                per_office=self.get_per_office_progress()))
