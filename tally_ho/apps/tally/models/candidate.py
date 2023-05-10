from django.db import models
from django.db.models import Q, Sum, Value as V
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.utils.templates import get_active_candidate_link


class Candidate(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot = models.ForeignKey(Ballot, related_name='candidates',
                               on_delete=models.PROTECT)
    candidate_id = models.PositiveIntegerField()
    full_name = models.TextField()
    order = models.PositiveSmallIntegerField()
    race_type = EnumIntegerField(RaceType, null=True)
    active = models.BooleanField(default=True)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='candidates',
                              on_delete=models.PROTECT)

    @property
    def race_type_name(self):
        return {
            RaceType.GENERAL: _('General'),
            RaceType.WOMEN: _('Women'),
            RaceType.COMPONENT_AMAZIGH: _('Component Amazigh'),
            RaceType.COMPONENT_TWARAG: _('Component Twarag'),
            RaceType.COMPONENT_TEBU: _('Component Tebu'),
            RaceType.PRESIDENTIAL: _('Presidential'),
        }[self.race_type]

    def num_votes(self, result_form=None, form_state=FormState.ARCHIVED):
        """Return the number of final active votes for this candidate in the
        result form.

        :param result_form: The result form to restrict the sum over votes to.
        :param form_state: The result form state, default is archived.

        :returns: The number of votes for this candidate and result form or a
            list of the number of results and the number of votes if a result
            form not is passed.
        """
        results = self.results.filter(
            entry_version=EntryVersion.FINAL,
            result_form__form_state=form_state,
            active=True)

        if result_form:
            results = results.filter(result_form=result_form)
            return results.aggregate(
                total_votes=Coalesce(Sum('votes'), V(0)))['total_votes']

        results = results.distinct('entry_version', 'active', 'result_form')

        # Distinct can not be combined with aggregate.
        return [len(results), sum([r.votes for r in results])]

    @property
    def num_valid_votes(self):
        """Return the number of final active votes for this candidate.

        :returns: The number of votes
        """
        results = self.results.filter(
            entry_version=EntryVersion.FINAL,
            result_form__form_state=FormState.ARCHIVED,
            active=True)

        results = results.distinct('entry_version', 'active', 'result_form')

        return sum([r.votes for r in results])

    @property
    def num_all_votes(self):
        """Return the number of final active votes plus votes in forms in
        quarantine for this candidate.

        :returns: The number of votes
        """
        results = self.results.filter(
            entry_version=EntryVersion.FINAL,
            active=True)

        results = results.filter(
            Q(result_form__form_state=FormState.ARCHIVED) |
            Q(result_form__form_state=FormState.AUDIT))

        results = results.distinct('entry_version', 'active', 'result_form')

        return sum([r.votes for r in results])

    @property
    def num_quarentine_votes(self):
        """Return the number of final active votes plus votes in forms in
        quarantine for this candidate.

        :returns: The number of votes
        """
        results = self.results.filter(
            entry_version=EntryVersion.FINAL,
            result_form__form_state=FormState.AUDIT,
            active=True)

        results = results.distinct('entry_version', 'active', 'result_form')

        return sum([r.votes for r in results])

    @property
    def ballot_number(self):
        return self.ballot.number

    @property
    def get_action_button(self):
        return get_active_candidate_link(self) if self else None


reversion.register(Candidate)
