from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.actions_prior import ActionsPrior


class Clearance(BaseModel):
    class Meta:
        app_label = 'tally'

    RESOLUTION_RECOMMENDATION = (
        (0, _('Issue Resolved - Re-sent')),
        (1, _('Pending Field Input')),
        (2, _('Pass to Administrator')),
        (3, _('Reset to Pre-Intake - Super-Supervisor to Approve')),
    )

    result_form = models.ForeignKey(ResultForm)
    supervisor = models.ForeignKey(User, null=True,
                                   related_name='clearance_user')
    user = models.ForeignKey(User)

    # Problem Fields
    center_name_missing = models.BooleanField(default=False)
    center_name_mismatching = models.BooleanField(default=False)
    center_code_missing = models.BooleanField(default=False)
    center_code_mismatching = models.BooleanField(default=False)
    form_already_in_system = models.BooleanField(default=False)
    form_incorrectly_entered_into_system = models.BooleanField(default=False)
    other = models.TextField(null=True)

    # Recommendations
    action_prior_to_recommendation = enum.EnumField(ActionsPrior)
    resolution_recommendation = models.PositiveSmallIntegerField(
        choices=RESOLUTION_RECOMMENDATION)

    # Comments
    audit_review_team_comments = models.TextField(null=True)
    supervisor_comment = models.TextField(null=True)
