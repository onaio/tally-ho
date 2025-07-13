from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from tally_ho.apps.tally.views import workflow as views
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.request_reason import RequestReason
from tally_ho.libs.models.enums.request_status import RequestStatus
from tally_ho.libs.models.enums.request_type import RequestType
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    create_ballot,
    create_candidate,
    create_electrol_race,
    create_result,
    create_result_form,
    create_reconciliation_form,
    create_tally,
    TestBase
)


class TestWorkflow(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self.tally = create_tally()
        self.electrol_race =\
            create_electrol_race(
                self.tally,
                election_level="Presidential",
                ballot_name="Presidential"
            )
        self.ballot =\
            create_ballot(
                self.tally,
                electrol_race=self.electrol_race,
                number=1
            )

    def _common_view_tests(self, view, tally=None):
        if not tally:
            tally = create_tally()
        request = self.factory.get('/')
        request.user = AnonymousUser()
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('/accounts/login/?next=/', response['location'])
        self._create_and_login_user()
        tally.users.add(self.user)
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            view(request, tally_id=tally.pk)
        return response

    def test_initiate_recall_get(self):
        """Test that audit clerks can access the initiate recall view."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)

        view = views.InitiateRecallView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b'Initiate Recall Request', response.content)

    def test_initiate_recall_post_success(self):
        """Test successful submission of recall initiation form."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        view = views.InitiateRecallView.as_view()
        data = {
            'barcode': result_form.barcode,
            'barcode_copy': result_form.barcode,
            'barcode_scan': '',
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            f"/tally/{tally.pk}/workflow/create-recall/", response['location'])
        self.assertEqual(
            request.session['recall_result_form_pk'], result_form.pk)

    def test_initiate_recall_post_not_archived(self):
        """Test that non-archived forms are rejected."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            barcode='123456789',
            tally=tally
        )

        view = views.InitiateRecallView.as_view()
        data = {
            'barcode': result_form.barcode,
            'barcode_copy': result_form.barcode,
            'barcode_scan': '',
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b'not in the ARCHIVED state', response.content)

    def test_initiate_recall_post_existing_request(self):
        """Test that duplicate recall requests are rejected."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        # Create an existing workflow request
        WorkflowRequest.objects.create(
            result_form=result_form,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            request_reason=RequestReason.DATA_ENTRY_ERROR,
            status=RequestStatus.PENDING,
            requester=self.user
        )

        view = views.InitiateRecallView.as_view()
        data = {
            'barcode': result_form.barcode,
            'barcode_copy': result_form.barcode,
            'barcode_scan': '',
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(
            b'An active recall request already exists', response.content)

    def test_create_recall_request_get(self):
        """Test the create recall request view."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        view = views.CreateRecallRequestView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {'recall_result_form_pk': result_form.pk}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b'Create Recall Request for Barcode', response.content)

    def test_create_recall_request_get_no_form_pk(self):
        """Test that accessing the create request view without a form
        redirects.
        """
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)

        view = views.CreateRecallRequestView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        configure_messages(request)
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            f"/audit/{tally.pk}/?tab=recalls", response['location'])

    def test_create_recall_request_post(self):
        """Test creating a recall request."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        view = views.CreateRecallRequestView.as_view()
        data = {
            'request_reason': RequestReason.DATA_ENTRY_ERROR.value,
            'request_comment': 'Test comment',
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        configure_messages(request)
        request.session = { 'recall_result_form_pk': result_form.pk }
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            f"/audit/{tally.pk}/?tab=recalls", response['location'])

        workflow_request = WorkflowRequest.objects.get(result_form=result_form)
        self.assertEqual(workflow_request.requester, self.user)
        self.assertEqual(
            workflow_request.request_type, RequestType.RECALL_FROM_ARCHIVE)
        self.assertEqual(workflow_request.status, RequestStatus.PENDING)
        self.assertEqual(
            workflow_request.request_reason, RequestReason.DATA_ENTRY_ERROR)

    def test_recall_request_detail_view(self):
        """Test viewing a recall request."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        workflow_request = WorkflowRequest.objects.create(
            result_form=result_form,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            status=RequestStatus.PENDING,
            requester=self.user,
            request_reason=RequestReason.DATA_ENTRY_ERROR,
        )

        view = views.RecallRequestDetailView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response =\
            view(request, tally_id=tally.pk, request_pk=workflow_request.pk)

        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b'Recall Request Details', response.content)
        self.assertIn(b'Data Entry Error', response.content)
        self.assertIn(b'View Form Details', response.content)

        self.assertNotIn(b'Approve Recall', response.content)

    def test_recall_request_detail_view_as_manager(self):
        """Test viewing a recall request as a tally manager."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        clerk = self._create_user(username='clerk')
        workflow_request = WorkflowRequest.objects.create(
            result_form=result_form,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            status=RequestStatus.PENDING,
            requester=clerk,
            request_reason=RequestReason.DATA_ENTRY_ERROR,
        )

        view = views.RecallRequestDetailView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response =\
            view(request, tally_id=tally.pk, request_pk=workflow_request.pk)

        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b'Recall Request Details', response.content)

        self.assertIn(b'Approve Recall', response.content)

    def test_approve_recall_request(self):
        """Test approving a recall request."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        # Create a request by another user
        clerk = self._create_user(username='clerk')
        workflow_request = WorkflowRequest.objects.create(
            result_form=result_form,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            status=RequestStatus.PENDING,
            requester=clerk,
            request_reason=RequestReason.DATA_ENTRY_ERROR,
        )

        view = views.RecallRequestDetailView.as_view()
        data = {
            'approval_comment': 'Approved for correction',
            'approve': 'Approve',
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)
        response =\
            view(request, tally_id=tally.pk, request_pk=workflow_request.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            f"/audit/{tally.pk}/?tab=recalls", response['location'])

        workflow_request.refresh_from_db()
        result_form.refresh_from_db()

        self.assertEqual(workflow_request.status, RequestStatus.APPROVED)
        self.assertEqual(workflow_request.approver, self.user)
        self.assertEqual(
            workflow_request.approval_comment, 'Approved for correction')
        self.assertEqual(result_form.form_state, FormState.AUDIT)

        # Check that an Audit record was created
        audit = Audit.objects.get(result_form=result_form)
        self.assertEqual(audit.user, self.user)

    def test_reject_recall_request(self):
        """Test rejecting a recall request."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )

        # Create a request by another user
        clerk = self._create_user(username='clerk')
        workflow_request = WorkflowRequest.objects.create(
            result_form=result_form,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            status=RequestStatus.PENDING,
            requester=clerk,
            request_reason=RequestReason.DATA_ENTRY_ERROR,
        )

        view = views.RecallRequestDetailView.as_view()
        data = {
            'approval_comment': 'Not necessary',
            'reject': 'Reject',
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)
        response =\
            view(request, tally_id=tally.pk, request_pk=workflow_request.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            f"/audit/{tally.pk}/?tab=recalls", response['location'])

        workflow_request.refresh_from_db()
        result_form.refresh_from_db()

        self.assertEqual(workflow_request.status, RequestStatus.REJECTED)
        self.assertEqual(workflow_request.approver, self.user)
        self.assertEqual(workflow_request.approval_comment, 'Not necessary')

        self.assertEqual(result_form.form_state, FormState.ARCHIVED)

    def test_view_result_form_details(self):
        """Test the view for displaying result form details."""
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.AUDIT_CLERK)
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.ARCHIVED,
            barcode='123456789',
            tally=tally
        )
        create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=0,
            number_valid_votes=50,
            number_of_voter_cards_in_the_ballot_box=50,
            number_sorted_and_counted=50,
        )
        candidate1 = create_candidate(self.ballot, "cand1", tally=self.tally)
        candidate2 = create_candidate(self.ballot, "cand2", tally=self.tally)

        create_result(result_form, candidate1, self.user, votes=25)
        create_result(result_form, candidate2, self.user, votes=25)

        view = views.ViewResultFormDetailsView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response =\
            view(request, tally_id=tally.pk, result_form_pk=result_form.pk)

        self.assertEqual(response.status_code, 200)
        response.render()
        self.assertIn(b'Result Form Details', response.content)
        self.assertIn(str(result_form.barcode).encode(), response.content)
        self.assertIn(b'Reconciliation Section', response.content)
        self.assertIn(b'Result Form Details Results Section', response.content)

def configure_messages(request):
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
