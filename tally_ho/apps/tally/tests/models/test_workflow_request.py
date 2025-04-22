from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest
from tally_ho.libs.models.enums.request_reason import RequestReason
from tally_ho.libs.models.enums.request_status import RequestStatus
from tally_ho.libs.models.enums.request_type import RequestType
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase, create_result_form, create_tally
)


class WorkflowRequestModelTestCase(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self.tally = create_tally()

        self.requester_user =\
            self._create_user(username='testrequester', password='password')
        self.requester_profile =\
            UserProfile.objects.get(pk=self.requester_user.pk)

        self.approver_user =\
            self._create_user(username='approver', password='password')
        self.approver_profile =\
            UserProfile.objects.get(pk=self.approver_user.pk)
        self._add_user_to_group(self.approver_user, groups.TALLY_MANAGER)

        self.super_admin_user =\
            self._create_user(username='superadmin', password='password')
        self._add_user_to_group(
            self.super_admin_user, groups.SUPER_ADMINISTRATOR)

        self.audit_clerk_user =\
            self._create_user(username='auditclerk', password='password')
        self._add_user_to_group(self.audit_clerk_user, groups.AUDIT_CLERK)
        self.audit_supervisor_user =\
            self._create_user(username='auditsupervisor', password='password')
        self._add_user_to_group(
            self.audit_supervisor_user, groups.AUDIT_SUPERVISOR)
        self.other_user =\
            self._create_user(username='other', password='pwd')

        self.result_form =\
            create_result_form(barcode='12345', tally=self.tally)
        self.workflow_request =\
            WorkflowRequest.objects.create(
                request_type=RequestType.RECALL_FROM_ARCHIVE,
                result_form=self.result_form,
                requester=self.requester_profile,
                request_reason=RequestReason.OTHER,
                request_comment="Test request"
        )

    def test_workflow_request_creation_defaults(self):
        """Test default status is PENDING."""
        self.assertEqual(self.workflow_request.status, RequestStatus.PENDING)
        self.assertIsNone(self.workflow_request.approver)
        self.assertIsNone(self.workflow_request.approval_comment)
        self.assertIsNone(self.workflow_request.resolved_date)

    def test_workflow_request_str(self):
        """Test string representation."""
        expected_str = (
            f"{self.workflow_request.get_request_type_display()} request for "
            f"{self.result_form.barcode} - Status: "
            f"{self.workflow_request.get_status_display()}"
        )
        self.assertEqual(str(self.workflow_request), expected_str)

    def test_is_pending(self):
        """Test is_pending method."""
        self.workflow_request.status = RequestStatus.PENDING
        self.workflow_request.save()
        self.assertTrue(self.workflow_request.is_pending())
        self.assertFalse(self.workflow_request.is_approved())
        self.assertFalse(self.workflow_request.is_rejected())

    def test_is_approved(self):
        """Test is_approved method."""
        self.workflow_request.status = RequestStatus.APPROVED
        self.workflow_request.save()
        self.assertFalse(self.workflow_request.is_pending())
        self.assertTrue(self.workflow_request.is_approved())
        self.assertFalse(self.workflow_request.is_rejected())

    def test_is_rejected(self):
        """Test is_rejected method."""
        self.workflow_request.status = RequestStatus.REJECTED
        self.workflow_request.save()
        self.assertFalse(self.workflow_request.is_pending())
        self.assertFalse(self.workflow_request.is_approved())
        self.assertTrue(self.workflow_request.is_rejected())

    def test_can_be_actioned_by(self):
        """Test can_be_actioned_by method with different user roles."""
        tally_manager = self.approver_user
        super_admin = self.super_admin_user
        audit_clerk = self.audit_clerk_user

        self.assertTrue(
            self.workflow_request.can_be_actioned_by(tally_manager))
        self.assertTrue(
            self.workflow_request.can_be_actioned_by(super_admin))
        self.assertFalse(
            self.workflow_request.can_be_actioned_by(audit_clerk))
        self.assertFalse(
            self.workflow_request.can_be_actioned_by(self.requester_user))

    def test_can_be_viewed_by(self):
        """Test can_be_viewed_by method with different user roles."""
        tally_manager = self.approver_user
        super_admin = self.super_admin_user
        audit_clerk = self.audit_clerk_user
        audit_supervisor = self.audit_supervisor_user
        other_user = self.other_user

        self.assertTrue(
            self.workflow_request.can_be_viewed_by(tally_manager))
        self.assertTrue(
            self.workflow_request.can_be_viewed_by(super_admin))
        self.assertTrue(
            self.workflow_request.can_be_viewed_by(audit_clerk))
        self.assertTrue(
            self.workflow_request.can_be_viewed_by(audit_supervisor))

        self._add_user_to_group(
            self.requester_user, groups.AUDIT_CLERK)
        self.assertTrue(
            self.workflow_request.can_be_viewed_by(self.requester_user))

        self.assertFalse(
            self.workflow_request.can_be_viewed_by(other_user))
