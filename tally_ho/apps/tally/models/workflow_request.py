# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.request_reason import RequestReason
from tally_ho.libs.models.enums.request_status import RequestStatus
from tally_ho.libs.models.enums.request_type import RequestType


@reversion.register()
class WorkflowRequest(BaseModel):
    class Meta:
        app_label = 'tally'
        indexes = [
            models.Index(fields=['result_form', 'request_type', 'status'])
        ]

    request_type = EnumIntegerField(
        RequestType, verbose_name=_("Request Type"))
    status = EnumIntegerField(
        RequestStatus,
        default=RequestStatus.PENDING,
        verbose_name=_("Request Status"))
    result_form = models.ForeignKey(
        ResultForm,
        on_delete=models.PROTECT,
        related_name='workflow_requests')
    tally = models.ForeignKey(Tally,
                              on_delete=models.PROTECT,
                              related_name='workflow_requests')
    requester = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name='initiated_requests')
    request_reason = EnumIntegerField(RequestReason, verbose_name=_("Reason"))
    request_comment = models.TextField(verbose_name=_("Request Comment"))
    approver = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name='approved_rejected_requests',
        null=True,
        blank=True)
    approval_comment = models.TextField(
        verbose_name=_("Approval/Rejection Comment"), null=True, blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(
            f"{self.get_request_type_display()} request for "
            f"{self.result_form.barcode} - Status: "
            f"{self.get_status_display()}")

    def is_pending(self):
        return self.status == RequestStatus.PENDING

    def is_approved(self):
        return self.status == RequestStatus.APPROVED

    def is_rejected(self):
        return self.status == RequestStatus.REJECTED

    def can_be_actioned_by(self, user):
        """
        Logic to determine if the user (Tally Manager/Super Admin)
        can approve/reject
        :param user: Logged in user
        :return: bool
        """
        from tally_ho.libs.permissions import groups
        return user.is_authenticated and\
            groups.is_tally_manager(user) or\
                groups.is_super_administrator(user)

    def can_be_viewed_by(self, user):
        """
        Logic to determine who can view the request
        Audit Clerks/Supervisors, or any
        Tally Manager/Super Admin
        :param user: Logged in user
        :return: bool
        """
        from tally_ho.libs.permissions import groups
        return (
            user.is_authenticated and (
                groups.is_audit_clerk(user) or
                groups.is_audit_supervisor(user) or
                groups.is_tally_manager(user) or
                groups.is_super_administrator(user)
            )
        )

    def save(self, *args, **kwargs):
        if not self.tally_id and self.result_form_id:
            self.tally_id = self.result_form.tally_id
        super().save(*args, **kwargs)
