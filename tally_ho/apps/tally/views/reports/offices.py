from django.views.generic import TemplateView
from django.http import HttpResponse
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.office import Office
from tally_ho.libs.permissions import groups
from tally_ho.libs.reports import progress as p
from tally_ho.libs.views import mixins


def getOverviews(tally_id):
    overviews = [
            p.ExpectedProgressReport(tally_id),
            p.IntakeProgressReport(tally_id),
            p.DataEntry1ProgressReport(tally_id),
            p.DataEntry2ProgressReport(tally_id),
            p.CorrectionProgressReport(tally_id),
            p.QualityControlProgressReport(tally_id),
            p.ArchivedProgressReport(tally_id),
            p.ClearanceProgressReport(tally_id),
            p.AuditProgressReport(tally_id),
            p.NotRecievedProgressReport(tally_id)
    ]

    return overviews


class OfficesReportView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'reports/offices.html'

    def get_per_office_progress(self):
        data = []
        tally_id = self.kwargs['tally_id']

        intaken = p.IntakenProgressReport(tally_id)
        not_intaken = p.NotRecievedProgressReport(tally_id)
        archived = p.ArchivedProgressReport(tally_id)
        valid_votes = p.ValidVotesProgressReport(tally_id)

        for office in Office.objects.filter(
                tally__id=tally_id).order_by('number'):
            intaken_results = intaken.for_center_office(office)
            not_intaken_results = not_intaken.for_center_office(office)
            archived_result = archived.for_center_office(office)
            total_valid_votes = valid_votes.for_center_office(
                office=office,
                query_valid_votes=True)
            data.append({
                'office': office.name,
                'number': office.number,
                'intaken': intaken_results,
                'not_intaken': not_intaken_results,
                'archived': archived_result,
                'valid_votes': total_valid_votes
            })

        return data

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']

        overviews = getOverviews(tally_id)
        per_office = self.get_per_office_progress()

        return self.render_to_response(
            self.get_context_data(
                overviews=overviews,
                per_office=per_office,
                tally_id=tally_id))


class OfficesReportDownloadView(OfficesReportView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'reports/offices.html'

    def get(self, *args, **kwargs):

        option = kwargs.get('option')
        tally_id = kwargs.get('tally_id')

        if option == 'overview':
            overviews = getOverviews(tally_id)

            result = "'number','percentage','forms'\r\n"

            for o in overviews:
                result += f"'{o.number}','{o.percentage}','{o.label}'\r\n"

        else:
            office_data = self.get_per_office_progress()

            result =\
                str("'not_intaken','intaken','archived','number','office'"
                    ",'valid_votes'\r\n")

            for data in office_data:
                result +=\
                    str(f"'{data['not_intaken']}','{data['intaken']}',"
                        f"'{data['archived']}','{data['number']}',"
                        f"'{data['office']}','{data['valid_votes']}'\r\n")

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = \
            f'attachment; filename="result_{option}.csv"'

        response.write(result)

        return response
