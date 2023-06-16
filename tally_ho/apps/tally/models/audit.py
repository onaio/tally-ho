from django.db import models
from django.utils.translation import gettext_lazy as _
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution
from tally_ho.libs.utils.collections import keys_if_value


class Audit(BaseModel):
    class Meta:
        app_label = 'tally'

    quarantine_checks = models.ManyToManyField(QuarantineCheck)
    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    supervisor = models.ForeignKey(UserProfile,
                                   related_name='audit_user',
                                   null=True,
                                   on_delete=models.PROTECT)
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    for_superadmin = models.BooleanField(default=False)
    reviewed_supervisor = models.BooleanField(default=False)
    reviewed_team = models.BooleanField(default=False)

    # Problem fields
    blank_reconciliation = models.BooleanField(default=False)
    blank_results = models.BooleanField(default=False)
    damaged_form = models.BooleanField(default=False)
    unclear_figures = models.BooleanField(default=False)
    other = models.TextField(null=True, blank=True)

    # Recommendations
    action_prior_to_recommendation = EnumIntegerField(ActionsPrior, blank=True,
                                                      null=True, default=4)
    resolution_recommendation = EnumIntegerField(
        AuditResolution, null=True, blank=True, default=0)

    # Comments
    team_comment = models.TextField(null=True, blank=True)
    supervisor_comment = models.TextField(null=True, blank=True)

    def get_problems(self):
        """Return a list of problems for this audit.

        Return a list of problems for which the problem checkbox has been
        selected.

        :returns: A list of strings.
        """
        problem_fields = {
            _('Blank Reconcilliation'): self.blank_reconciliation,
            _('Blank Results'): self.blank_results,
            _('Damaged Form'): self.damaged_form,
            _('Unclear Figures'): self.unclear_figures,
            _('Other'): self.other,
        }

        return keys_if_value(problem_fields)

    def action_prior_name(self):
        return _(self.action_prior_to_recommendation.label)

    def resolution_recommendation_name(self):
        return _(self.resolution_recommendation.label)


reversion.register(Audit)
