from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from libya_tally.apps.tally.models.quarantine_check import QuarantineCheck
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.actions_prior import ActionsPrior
from libya_tally.libs.models.enums.audit_resolution import AuditResolution


class Audit(BaseModel):
    class Meta:
        app_label = 'tally'

    quarantine_checks = models.ManyToManyField(QuarantineCheck)
    result_form = models.ForeignKey(ResultForm)
    supervisor = models.ForeignKey(User, related_name='audit_user', null=True)
    user = models.ForeignKey(User)

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
    action_prior_to_recommendation = enum.EnumField(ActionsPrior, blank=True,
                                                    null=True)
    resolution_recommendation = enum.EnumField(
        AuditResolution, null=True, blank=True)

    # Comments
    team_comment = models.TextField(null=True, blank=True)
    supervisor_comment = models.TextField(null=True, blank=True)

    def get_problems(self):
        problem_fields = {
            _('Blank Reconcilliation'): self.blank_reconciliation,
            _('Blank Results'): self.blank_results,
            _('Damaged Form'): self.damaged_form,
            _('Unclear Figures'): self.unclear_figures,
            _('Other'): self.other,
        }

        problems = []
        for problem_name, problem_field in problem_fields.iteritems():
            if problem_field:
                problems.append(problem_name)

        return problems

    def action_prior_name(self):
        return ActionsPrior.label(self.action_prior_to_recommendation)

    def resolution_recommendation_name(self):
        return AuditResolution.label(self.resolution_recommendation)

reversion.register(Audit)
