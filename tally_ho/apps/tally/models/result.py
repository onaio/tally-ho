from django.db import models
from enumfields import EnumIntegerField
import reversion
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest


class Result(BaseModel):
    class Meta:
        app_label = 'tally'

    candidate = models.ForeignKey(Candidate,
                                  related_name='results',
                                  on_delete=models.PROTECT)
    result_form = models.ForeignKey(ResultForm,
                                    related_name='results',
                                    on_delete=models.PROTECT)
    tally = models.ForeignKey(Tally,
                              on_delete=models.PROTECT,
                              default=1,
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


reversion.register(Result)
