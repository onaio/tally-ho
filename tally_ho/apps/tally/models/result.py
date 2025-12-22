from django.db import models
from django.db.models import Q
from enumfields import EnumIntegerField
import reversion
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest


class Result(BaseModel):
    class Meta:
        app_label = 'tally'
        indexes = [
            # Optimize candidate vote calculations in exports
            models.Index(fields=['candidate', 'entry_version', 'active', 'result_form']),
            # Optimize filtering by form state
            models.Index(fields=['result_form', 'entry_version', 'active']),
        ]

    candidate = models.ForeignKey(Candidate,
                                  related_name='results',
                                  on_delete=models.PROTECT)
    result_form = models.ForeignKey(ResultForm,
                                    related_name='results',
                                    on_delete=models.PROTECT)
    tally = models.ForeignKey(Tally,
                              on_delete=models.PROTECT,
                              related_name='results')
    user = models.ForeignKey(UserProfile,
                             null=True,
                             on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    entry_version = EnumIntegerField(EntryVersion)
    votes = models.PositiveIntegerField()
    deactivated_by_request = models.ForeignKey(
        WorkflowRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deactivated_results',
        help_text=_(str("The workflow request that triggered the "
                        "deactivation of this result record."))
    )

    def save(self, *args, **kwargs):
        if not self.tally_id and self.result_form_id:
            self.tally_id = self.result_form.tally_id
        super().save(*args, **kwargs)

    @classmethod
    def get_num_votes_for_all_candidates(cls, tally_id):
        """
        Batch version of Candidate.num_votes() for all candidates in a tally.
        Returns archived results with candidate_id, result_form_id, and votes.

        This is an optimized batch query that replaces multiple individual
        Candidate.num_votes() calls to avoid N+1 query problems.

        :param tally_id: The tally ID to filter by
        :returns: Queryset of distinct archived results
        """
        return cls.objects.filter(
            candidate__ballot__tally__id=tally_id,
            entry_version=EntryVersion.FINAL,
            active=True,
            result_form__form_state=FormState.ARCHIVED
        ).values('candidate_id', 'result_form_id', 'votes').distinct()

    @classmethod
    def get_num_all_votes_for_all_candidates(cls, tally_id):
        """
        Batch version of Candidate.num_all_votes for all candidates in a tally.
        Returns archived + audit results with candidate_id, result_form_id, and votes.

        This is an optimized batch query that replaces multiple individual
        Candidate.num_all_votes calls to avoid N+1 query problems.

        :param tally_id: The tally ID to filter by
        :returns: Queryset of distinct archived and audit results
        """
        return cls.objects.filter(
            candidate__ballot__tally__id=tally_id,
            entry_version=EntryVersion.FINAL,
            active=True
        ).filter(
            Q(result_form__form_state=FormState.ARCHIVED) |
            Q(result_form__form_state=FormState.AUDIT)
        ).values('candidate_id', 'result_form_id', 'votes').distinct()


reversion.register(Result)
