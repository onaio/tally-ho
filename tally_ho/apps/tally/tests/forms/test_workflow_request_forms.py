from tally_ho.libs.tests.test_base import (
    TestBase, create_tally, create_result_form
)
from tally_ho.apps.tally.forms.workflow_request_forms import (
    RequestRecallForm, ApprovalForm
)
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest
from tally_ho.libs.models.enums.request_reason import RequestReason
from tally_ho.libs.models.enums.request_type import RequestType
from tally_ho.libs.models.enums.form_state import FormState


class TestRequestRecallForm(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self.result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1, tally=self.tally)

        self.workflow_request = WorkflowRequest.objects.create(
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            result_form=self.result_form,
            requester=self.user,
            request_reason=RequestReason.INCORRECT_ARCHIVE,
            request_comment="Initial comment"
        )

    def test_blank_data(self):
        """Test form validation with blank data."""
        form = RequestRecallForm(data={}, instance=self.workflow_request)
        self.assertFalse(form.is_valid())
        self.assertIn('request_reason', form.errors)
        self.assertIn('request_comment', form.errors)
        self.assertTrue(form.fields['request_comment'].required)

    def test_missing_comment(self):
        """Test form validation with only reason provided
        (comment is required).
        """
        form = RequestRecallForm(
            data={
                'request_reason': RequestReason.INCORRECT_ARCHIVE.value
            },
            instance=self.workflow_request
        )
        self.assertFalse(form.is_valid())
        self.assertNotIn('request_reason', form.errors)
        self.assertIn('request_comment', form.errors)
        self.assertEqual(
            form.errors['request_comment'], ['This field is required.'])

    def test_valid_data(self):
        """Test form validation with valid data."""
        data = {
            'request_reason': RequestReason.OTHER.value,
            'request_comment': 'This is a valid test comment for recall.',
        }
        form = RequestRecallForm(data=data, instance=self.workflow_request)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.pk, self.workflow_request.pk)
        self.assertEqual(instance.request_reason, RequestReason.OTHER)
        self.assertEqual(
            instance.request_comment,
            'This is a valid test comment for recall.')


class TestApprovalForm(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self.result_form = create_result_form(
            form_state=FormState.QUALITY_CONTROL, tally=self.tally)
        # Create a base instance for the form to update
        self.workflow_request = WorkflowRequest.objects.create(
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            result_form=self.result_form,
            requester=self.user,
            request_reason=RequestReason.OTHER,
            request_comment="Requesting QC authorization"
        )

    def test_blank_data(self):
        """Test form validation with blank data (comment is optional)."""
        form = ApprovalForm(data={}, instance=self.workflow_request)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.approval_comment, "")

    def test_valid_data(self):
        """Test form validation with valid data."""
        data = {
            'approval_comment': 'This request is approved.',
        }
        form = ApprovalForm(data=data, instance=self.workflow_request)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(
            instance.pk, self.workflow_request.pk)
        self.assertEqual(
            instance.approval_comment, 'This request is approved.')

    def test_update_existing_comment(self):
        """Test updating an existing approval comment."""
        # Set an initial comment
        self.workflow_request.approval_comment = "Initial approval comment."
        self.workflow_request.save()

        data = {
            'approval_comment': 'Updated approval comment.',
        }
        form = ApprovalForm(data=data, instance=self.workflow_request)
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(
            instance.pk, self.workflow_request.pk)
        self.assertEqual(
            instance.approval_comment, 'Updated approval comment.')
