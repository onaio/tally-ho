from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.ballot import (
    form_ballot_numbers,
    race_type_name,
    sub_constituency,
    document_name,
)
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.views.exports import valid_ballots
from tally_ho.libs.permissions import groups
from tally_ho.libs.reports import progress as p
from tally_ho.libs.views import mixins


class RacesReportView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'reports/races.html'

    def get_per_ballot_progress(self):
        data = []
        tally_id = self.kwargs.get('tally_id')

        archived = p.ArchivedProgressReport(tally_id)
        sc_cache = SubConstituency.objects.all()
        sc_cache = dict(zip(map(lambda x: x.id, sc_cache), sc_cache))
        for d in valid_ballots(tally_id).values('id',
                                                'active',
                                                'race_type',
                                                'sc_component',
                                                'sc_presidential',
                                                'sc_general',
                                                'sc_women',
                                                'number',
                                                'document'):
            archived_result = archived.for_ballot(
                form_ballot_numbers=form_ballot_numbers(d['number']))
            sc = sub_constituency(sc_cache.get(d['sc_component']),
                                  sc_cache.get(d['sc_women']),
                                  sc_cache.get(d['sc_general']),
                                  sc_cache.get(d['sc_presidential']))

            if sc:
                data.append({
                    'ballot': d['number'],
                    'district': sc.code,
                    'race_type': race_type_name(d['race_type'],
                                                sc_cache.get(d['sc_general'])),
                    'document': d['document'],
                    'document_name': document_name(d['document']),
                    'expected': archived_result['denominator'],
                    'complete': archived_result['number'],
                    'percentage': archived_result['percentage'],
                    'id': d['id'],
                    'active': d['active']
                })

        return data

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']

        per_ballot = self.get_per_ballot_progress()
        races = len(per_ballot)
        completed = sum([1 for x in per_ballot if isinstance(
            x['percentage'], float) and x['percentage'] >= 100])

        overview = {
            'races': races,
            'completed': completed,
            'percentage': p.rounded_percent(completed, races)
        }

        return self.render_to_response(
            self.get_context_data(
                overview=overview,
                per_ballot=per_ballot,
                tally_id=tally_id))
