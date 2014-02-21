from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.libs.permissions import groups
from libya_tally.libs.reports import progress as p
from libya_tally.libs.views import mixins


class RacesReportView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'tally/reports/races.html'

    def get_per_ballot_progress(self):
        data = []

        for ballot in Ballot.objects.all():
            archived = p.ArchivedProgressReport().for_ballot(ballot)
            sc = ballot.sc_general.all() or ballot.sc_women.all() or\
                ballot.sc_component.all()

            if sc:
                sc = sc[0]
                data.append({
                    'ballot': ballot.number,
                    'district': sc.code,
                    'race_type': ballot.race_type_name,
                    'expected': archived.denominator,
                    'complete': archived.number,
                    'percentage': archived.percentage,
                })

        return data

    def get(self, *args, **kwargs):
        per_ballot = self.get_per_ballot_progress()

        overview = {
            'races': len(per_ballot),
            'completed': reduce(lambda x, y: x + 1 if y['percentage'] == 100
                                else 0, per_ballot, 0),
        }

        overview['percentage'] = float(overview['completed']) / float(
            overview['races']) * 100

        return self.render_to_response(
            self.get_context_data(
                overview=overview,
                per_ballot=per_ballot))
