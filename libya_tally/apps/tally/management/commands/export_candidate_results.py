from collections import OrderedDict
import csv

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState

OUTPUT_PATH = 'results/candidate_votes.csv'


def get_votes(candidate):
    """Return the active results for this candidate that are for archived
    result forms."""
    votes = candidate.results.filter(
        entry_version=EntryVersion.FINAL,
        active=True, result_form__form_state=FormState.ARCHIVED).count()

    return votes


class Command(BaseCommand):
    help = ugettext_lazy("Export candidate votes list.")

    def handle(self, *args, **kwargs):
        self.export_candidate_votes()

    def export_candidate_votes(self):
        header = ['ballot number']

        max_candidates = 0
        for ballot in Ballot.objects.all():
            if ballot.candidates.count() > max_candidates:
                max_candidates = ballot.candidates.count()

        for i in xrange(1, max_candidates + 1):
            header.append('candidate %s name' % i)
            header.append('candidate %s votes' % i)

        with open(OUTPUT_PATH, 'wb') as f:
            # BOM, Excel needs it to open UTF-8 file properly
            f.write(u'\ufeff'.encode('utf8'))
            w = csv.DictWriter(f, header)
            w.writeheader()

            for ballot in Ballot.objects.all():
                output = OrderedDict({
                    'ballot number': ballot.number})

                for candidate in ballot.candidates.all():
                    votes = get_votes(candidate)
                    output['candidate %s name' % candidate.order] =\
                        candidate.full_name
                    output['candidate %s votes' % candidate.order] = votes

                w.writerow({k: v.encode('utf8') if isinstance(v, basestring)
                            else v for k, v in output.items()})
