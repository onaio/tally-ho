from django.contrib.auth.models import User
from django.db import models
from django_enumfield import enum

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
    for_supervisor = models.BooleanField(default=False)

    # Problem fields
    blank_reconciliation = models.BooleanField(default=False)
    blank_results = models.BooleanField(default=False)
    damaged_form = models.BooleanField(default=False)
    unclear_figures = models.BooleanField(default=False)
    other = models.TextField(null=True)

    # Recommendations
    action_prior_to_recommendation = enum.EnumField(ActionsPrior)
    resolution_recommendation = enum.EnumField(
        AuditResolution, null=True, blank=True)

    # Comments
    audit_review_team_comments = models.TextField(null=True)
    supervisor_comment = models.TextField(null=True)
