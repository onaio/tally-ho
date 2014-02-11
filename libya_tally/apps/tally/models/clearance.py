from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.actions_prior import ActionsPrior
from libya_tally.libs.models.enums.clearance_resolution import\
    ClearanceResolution


class Clearance(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm, related_name='clearances')
    supervisor = models.ForeignKey(User, null=True,
                                   related_name='clearance_user')
    user = models.ForeignKey(User)

    active = models.BooleanField(default=True)
    for_superadmin = models.BooleanField(default=False)
    reviewed_supervisor = models.BooleanField(default=False)
    reviewed_team = models.BooleanField(default=False)
    date_supervisor_modified = models.DateTimeField(null=True)
    date_team_modified = models.DateTimeField(null=True)

    # Problem Fields
    center_name_missing = models.BooleanField(default=False)
    center_name_mismatching = models.BooleanField(default=False)
    center_code_missing = models.BooleanField(default=False)
    center_code_mismatching = models.BooleanField(default=False)
    form_already_in_system = models.BooleanField(default=False)
    form_incorrectly_entered_into_system = models.BooleanField(default=False)
    other = models.TextField(null=True, blank=True)

    # Recommendations
    action_prior_to_recommendation = enum.EnumField(ActionsPrior)
    resolution_recommendation = enum.EnumField(
        ClearanceResolution, null=True, blank=True)

    # Comments
    team_comment = models.TextField(null=True, blank=True)
    supervisor_comment = models.TextField(null=True, blank=True)

    def get_problems(self):
        problem_fields = {
            _('Center Name Missing'): self.center_name_missing,
            _('Center Name Mismatching'): self.center_name_mismatching,
            _('Center Code Missing'): self.center_code_missing,
            _('Station Number Mismatching'): self.center_code_mismatching,
            _('Form Already in System'): self.form_already_in_system,
            _('Form Incorrectly Entered into the System'):
            self.form_incorrectly_entered_into_system,
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
        return ClearanceResolution.label(self.resolution_recommendation)


reversion.register(Clearance)
