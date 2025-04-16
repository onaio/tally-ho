# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import get_object_or_404, redirect, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, CreateView, DetailView
from django.views.generic.edit import FormMixin
from django import forms

from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.forms.recon_form import ReconForm
from tally_ho.apps.tally.forms.workflow_request_forms import (
    ApprovalForm, RequestRecallForm
)
from tally_ho.apps.tally.models import ResultForm, WorkflowRequest
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.views.quality_control import result_form_results
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.request_status import RequestStatus
from tally_ho.libs.models.enums.request_type import RequestType
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from guardian.mixins import LoginRequiredMixin


class AuditUserRequiredMixin(AccessMixin):
    """Verify that the current user is an Audit Clerk or Supervisor."""
    def dispatch(self, request, *args, **kwargs):
        if not (groups.is_audit_clerk(request.user) or
                groups.is_audit_supervisor(request.user)):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class ApproverUserRequiredMixin(AccessMixin):
    """Verify that the current user is a Tally Manager or Super Admin."""
    def dispatch(self, request, *args, **kwargs):
        if not (groups.is_tally_manager(request.user) or
                groups.is_super_administrator(request.user)):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class WorkflowPermissionMixin(AccessMixin):
    """Verify user can view the request."""
    def dispatch(self, request, *args, **kwargs):
        workflow_request = self.get_object()
        if not workflow_request.can_be_viewed_by(request.user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


# Archive Recall Views
class InitiateRecallView(LoginRequiredMixin,
                         AuditUserRequiredMixin,
                         mixins.TallyAccessMixin,
                         FormView):
    form_class = BarcodeForm
    template_name = 'barcode_verify.html'
    success_url_name = 'create_recall_request'

    def get_initial(self):
        initial = super().get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')
        context['header_text'] = _('Initiate Recall Request - Enter Barcode')
        context['form_action'] =\
            reverse(
                'initiate_recall_request',
                kwargs={'tally_id': self.kwargs.get('tally_id')})
        return context

    def form_valid(self, form):
        barcode = form.cleaned_data.get('barcode') or\
                  form.cleaned_data.get('barcode_scan')
        tally_id = form.cleaned_data.get('tally_id')

        try:
            result_form = ResultForm.objects.get(
                barcode=barcode, tally__id=tally_id)

            # --- Validation moved here ---
            if result_form.form_state != FormState.ARCHIVED:
                form.add_error(None, forms.ValidationError(
                    _("This form (%(barcode)s) is not in the ARCHIVED state."),
                    params={'barcode': barcode},
                ))
                return self.form_invalid(form)

            if WorkflowRequest.objects.filter(
                result_form=result_form,
                request_type=RequestType.RECALL_FROM_ARCHIVE,
                status=RequestStatus.PENDING).exists():
                form.add_error(None, forms.ValidationError(
                    _(str("An active recall request already exists for form "
                          "%(barcode)s.")),
                    params={'barcode': barcode},
                ))
                return self.form_invalid(form)

            self.request.session['recall_result_form_pk'] = result_form.pk
            return redirect(self.get_success_url(tally_id=tally_id))

        except ResultForm.DoesNotExist:
            form.add_error('barcode', forms.ValidationError(
                 _("No result form found with this barcode in this tally.")))
            return self.form_invalid(form)

    def get_success_url(self, **kwargs):
        return reverse(self.success_url_name, kwargs=kwargs)


class CreateRecallRequestView(LoginRequiredMixin,
                              AuditUserRequiredMixin,
                              mixins.TallyAccessMixin,
                              CreateView):
    model = WorkflowRequest
    form_class = RequestRecallForm
    template_name = 'workflow/recall_request_form.html'
    success_url_name = 'audit_dashboard'

    def dispatch(self, request, *args, **kwargs):
        # Ensure the PK is in the session
        if 'recall_result_form_pk' not in request.session:
            messages.error(request, _("No result form selected for recall."))
            return redirect(
                self.get_success_url(tally_id=self.kwargs.get('tally_id')))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tally_id = self.kwargs.get('tally_id')
        result_form_pk = self.request.session.get('recall_result_form_pk')
        context['result_form'] =\
            get_object_or_404(
                ResultForm, pk=result_form_pk, tally__id=tally_id)
        context['tally_id'] = tally_id
        context['header_text'] =\
            _('Create Recall Request for Barcode: {}').format(
                context['result_form'].barcode)
        return context

    def form_valid(self, form):
        tally_id = self.kwargs.get('tally_id')
        result_form_pk = self.request.session.get('recall_result_form_pk')
        result_form =\
            get_object_or_404(
                ResultForm, pk=result_form_pk, tally__id=tally_id)

        # Double check state and existing requests just before saving
        if result_form.form_state != FormState.ARCHIVED:
            messages.error(
                self.request, _("Form is no longer in ARCHIVED state."))
            return redirect(
                self.get_success_url(tally_id=tally_id))
        if WorkflowRequest.objects.filter(
            result_form=result_form,
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            status=RequestStatus.PENDING).exists():
            messages.error(
                self.request,
                _("An active recall request already exists for this form."))
            return redirect(
                self.get_success_url(tally_id=tally_id))

        form.instance.result_form = result_form
        form.instance.requester = self.request.user.userprofile
        form.instance.request_type = RequestType.RECALL_FROM_ARCHIVE

        self.object = form.save()

        messages.success(
            self.request,
            _("Recall request created successfully for barcode {}").format(
                result_form.barcode))
        # Clean up session
        del self.request.session['recall_result_form_pk']
        # Return the redirect directly
        return redirect(self.get_success_url(tally_id=tally_id))

    def get_success_url(self, **kwargs):
        return reverse(self.success_url_name, kwargs=kwargs) + '?tab=recalls'


class ViewResultFormDetailsView(LoginRequiredMixin,
                                mixins.TallyAccessMixin,
                                DetailView):
    """Displays Recon and Results details for a specific ResultForm."""
    model = ResultForm
    template_name = 'workflow/view_result_form_details.html'
    context_object_name = 'result_form'
    pk_url_kwarg = 'result_form_pk'

    def get_queryset(self):
        # Ensure the result form belongs to the correct tally
        return super().get_queryset().filter(
            tally__id=self.kwargs.get('tally_id'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result_form = self.get_object()
        tally_id = self.kwargs.get('tally_id')

        context['tally_id'] = tally_id
        context['header_text'] = _('Result Form Details')

        context['return_url_name'] = self.request.GET.get(
            'return_url_name', 'create_recall_request')
        context['request_pk'] = self.request.GET.get('request_pk')

        try:
            if self.request.GET.get('request_status') ==\
                RequestStatus.APPROVED.name:
                recon_model_instance = ReconciliationForm.objects.filter(
                    result_form=result_form,
                    result_form__tally=result_form.tally,
                    entry_version=EntryVersion.FINAL,
                    active=False,
                    deactivated_by_request__pk=\
                        self.request.GET.get('request_pk')
                ).first()
                context['reconciliation_form'] = ReconForm(
                    data=forms.model_to_dict(recon_model_instance))
            else:
                recon_model_instance = result_form.reconciliationform
                context['reconciliation_form'] = ReconForm(
                    data=forms.model_to_dict(recon_model_instance))
        except ResultForm.reconciliationform.RelatedObjectDoesNotExist:
            context['reconciliation_form'] = None
        except AttributeError:
             context['reconciliation_form'] = None

        try:
            if self.request.GET.get('request_status') == \
                RequestStatus.APPROVED.name:
                context['results'] =\
                    result_form_results(
                        result_form=result_form,
                        active=False,
                        workflow_request_pk=self.request.GET.get('request_pk')
                    )
            else:
                context['results'] =\
                    result_form_results(result_form=result_form)
        except ResultForm.results.RelatedObjectDoesNotExist:
            context['results'] = None
        return context


class RecallRequestDetailView(LoginRequiredMixin,
                              WorkflowPermissionMixin,
                              mixins.TallyAccessMixin,
                              FormMixin, # For handling the approval form
                              DetailView):
    model = WorkflowRequest
    form_class = ApprovalForm
    template_name = 'workflow/recall_request_detail.html'
    context_object_name = 'request'
    pk_url_kwarg = 'request_pk'
    success_url_name = 'audit_dashboard'

    def get_queryset(self):
        # Ensure we only get recall requests for the correct tally
        return super().get_queryset().filter(
            request_type=RequestType.RECALL_FROM_ARCHIVE,
            result_form__tally__id=self.kwargs.get('tally_id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')
        workflow_request = self.get_object()
        context['can_action'] =\
            workflow_request.is_pending() and \
                (groups.is_tally_manager(self.request.user) or
                    groups.is_super_administrator(self.request.user))
        if context['can_action']:
             context['approval_form'] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        # Check if user is an approver
        if not (groups.is_tally_manager(request.user) or
                groups.is_super_administrator(request.user)):
            return self.handle_no_permission()

        workflow_request = self.get_object()
        result_form = workflow_request.result_form
        tally_id = self.kwargs.get('tally_id')

        # Check if already actioned
        if not workflow_request.is_pending():
            messages.warning(
                request, _("This request has already been actioned."))
            return redirect(
                    self.get_success_url(tally_id=tally_id))

        form = self.get_form()
        if form.is_valid():
            approval_comment = form.cleaned_data.get('approval_comment')

            if 'approve' in request.POST:
                # Check form state again
                if result_form.form_state != FormState.ARCHIVED:
                     messages.error(
                         request,
                         _(str("Form is no longer in ARCHIVED state."
                               " Cannot approve recall.")))
                     return redirect(
                                self.get_success_url(tally_id=tally_id))

                workflow_request.status = RequestStatus.APPROVED
                # Move form back to Audit
                result_form.reject(
                    new_state=FormState.AUDIT,
                    reject_reason=approval_comment,
                    workflow_request=workflow_request
                )
                # Create an audit record for the form
                Audit.objects.create(
                    result_form=result_form, user=request.user.userprofile)
                workflow_request.save()
                messages.success(
                    request,
                    _(str("Recall request for barcode "
                          f"{result_form.barcode} approved.")))

            elif 'reject' in request.POST:
                workflow_request.status = RequestStatus.REJECTED
                workflow_request.approver = request.user.userprofile
                workflow_request.approval_comment = approval_comment
                workflow_request.resolved_date = timezone.now()
                workflow_request.save()
                messages.success(
                    request,
                    _(str("Recall request for barcode "
                          f"{result_form.barcode} rejected.")))
            else:
                messages.error(request, _("Invalid action."))
                return self.form_invalid(form)

            workflow_request.approver = request.user.userprofile
            workflow_request.approval_comment = approval_comment
            workflow_request.resolved_date = timezone.now()
            workflow_request.save()

            return redirect(
                self.get_success_url(tally_id=tally_id))
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Please correct the errors below."))
        return super().form_invalid(form)

    def get_success_url(self, **kwargs):
        return reverse(self.success_url_name, kwargs=kwargs) + '?tab=recalls'
