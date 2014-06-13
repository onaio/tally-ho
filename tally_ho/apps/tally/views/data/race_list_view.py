from django.views.generic import TemplateView
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.views.reports.races import RacesReportView
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.views.pagination import paging


class RaceListView(RacesReportView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/races.html"

    def get(self, *args, **kwargs):
        ballots = self.get_per_ballot_progress()
        ballots = paging(ballots, self.request)

        return self.render_to_response(
            self.get_context_data(
                ballots=ballots))
