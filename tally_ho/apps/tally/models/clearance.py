from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.clearance_resolution import\
    ClearanceResolution
from tally_ho.libs.utils.collections import keys_if_value


class Clearance(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm, related_name='clearances',
                                    on_delete=models.PROTECT)
    supervisor = models.ForeignKey(User, null=True,
                                   on_delete=models.PROTECT,
                                   related_name='clearance_user')
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
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
    action_prior_to_recommendation = EnumIntegerField(
        ActionsPrior, blank=True, null=True, default=4)
    resolution_recommendation = EnumIntegerField(
        ClearanceResolution, null=True, blank=True, default=0)

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

        return keys_if_value(problem_fields)

    def action_prior_name(self):
        return self.action_prior_to_recommendation.name

    def resolution_recommendation_name(self):
        return ClearanceResolution.label(self.resolution_recommendation)


reversion.register(Clearance)
