from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum

from libya_tally.apps.tally.models.quarantine_check import QuarantineCheck
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.actions_prior import ActionsPrior


class Audit(BaseModel):
    class Meta:
        app_label = 'tally'

    RESOLUTION_RECOMMENDATION = (
        (0, _('No Problem - Return to DE 1')),
        (1, _('Clarified Figures - Return to DE 1')),
        (2, _('Other Correction - Return to DE 1')),
        (3, _('Make Available for Archive - Super-Supervisor to Approve')),
    )

    quarantine_checks = models.ManyToManyField(QuarantineCheck)
    result_form = models.ForeignKey(ResultForm)
    supervisor = models.ForeignKey(User, related_name='audit_user', null=True)
    user = models.ForeignKey(User)

    active = models.BooleanField(default=True)

    # Problem fields
    blank_reconciliation = models.BooleanField(default=False)
    blank_results = models.BooleanField(default=False)
    damaged_form = models.BooleanField(default=False)
    unclear_figures = models.BooleanField(default=False)
    other = models.TextField(null=True)

    # Recommendations
    action_prior_to_recommendation = enum.EnumField(ActionsPrior)
    resolution_recommendation = models.PositiveSmallIntegerField(
        choices=RESOLUTION_RECOMMENDATION)

    # Comments
    audit_review_team_comments = models.TextField(null=True)
    supervisor_comment = models.TextField(null=True)
