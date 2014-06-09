from django.views.generic import TemplateView
from django.http import HttpResponse
from guardian.mixins import LoginRequiredMixin
from djqscsv import render_to_csv_response

from tally_ho.apps.tally.models.office import Office
from tally_ho.libs.permissions import groups
from tally_ho.libs.reports import progress as p
from tally_ho.libs.views import mixins

def getOverviews():
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

    return overviews

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
        overviews = getOverviews()

        return self.render_to_response(
            self.get_context_data(
                overviews=overviews,
                per_office=self.get_per_office_progress()))

class OfficesReportDownloadView(OfficesReportView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'reports/offices.html'

    def get(self, *args, **kwargs):

        option = kwargs.get('option')

        if option == 'overview':
            overviews = getOverviews()

            result = "'number','percentage','forms'\r\n"

            for o in overviews:
                result += "'%s','%s','%s'\r\n" % (o.number, o.percentage, o.label)

        else:
            office_data = self.get_per_office_progress()

            result = "'not_intaken','intaken','archived','number','office'\r\n"

            for data in office_data:
                result += "'%s','%s','%s','%s','%s'\r\n" % \
                                    (data['not_intaken'], data['intaken'], data['archived'],
                                        data['number'], data['office'],)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="result_%s.csv"' % option

        response.write(result)

        return response
