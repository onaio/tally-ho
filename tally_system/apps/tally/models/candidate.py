from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from tally_system.apps.tally.models.ballot import Ballot
from tally_system.libs.models.base_model import BaseModel
from tally_system.libs.models.enums.entry_version import EntryVersion
from tally_system.libs.models.enums.form_state import FormState
from tally_system.libs.models.enums.race_type import RaceType


class Candidate(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot = models.ForeignKey(Ballot, related_name='candidates')

    candidate_id = models.PositiveIntegerField()
    full_name = models.TextField()
    order = models.PositiveSmallIntegerField()
    race_type = enum.EnumField(RaceType)

    @property
    def race_type_name(self):
        return {
            0: _('General'),
            1: _('Women'),
            2: _('Component Amazigh'),
            3: _('Component Twarag'),
            4: _('Component Tebu')
        }[self.race_type]

    def num_votes(self, result_form=None):
        """Return the number of final active votes for this candidate in the
        result form.

        :param result_form: The result form to restrict the sum over votes to.

        :returns: The number of votes for this candidate and result form or a
            list of the number of results and the number of votes if a result
            form not is passed.
        """
        results = self.results.filter(
            entry_version=EntryVersion.FINAL,
            result_form__form_state=FormState.ARCHIVED,
            active=True)

        if result_form:
            results = results.filter(result_form=result_form)
            return results.aggregate(models.Sum('votes')).values()[0] or 0

        results = results.distinct('entry_version', 'active', 'result_form')

        # Distinct can not be combined with aggregate.
        return [len(results), sum([r.votes for r in results])]


reversion.register(Candidate)
