import csv

import dateutil.parser
from django.core.serializers.json import DjangoJSONEncoder, json
from django.forms import model_to_dict
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.audit_form import AuditForm
from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.forms.recon_form import ReconForm
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest
from tally_ho.apps.tally.views.quality_control import result_form_results
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.request_type import RequestType
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.form_state import form_in_state, safe_form_in_state
from tally_ho.libs.views.mixins import (
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    TallyAccessMixin,
)
from tally_ho.libs.views.pagination import paging
from tally_ho.libs.views.session import session_matches_post_result_form


def save_result_form_processing_stats(
        request,
        encoded_start_time,
        result_form,
        approved_by_supervisor=False,
        reviewed_by_supervisor=False):
    """Save result form processing stats.

    :param request: The request object.
    :param encoded_start_time: The encoded time the result form started
        to be processed.
    :param result_form: The result form being processed by the audit clerk.
    :param approved_by_supervisor: True the result form was
        approved by supervisor.
    :param reviewed_by_supervisor: True the result form was
        reviewed by supervisor.
    """
    audit_start_time = dateutil.parser.parse(
        encoded_start_time)
    del request.session['encoded_result_form_audit_start_time']

    audit_end_time = timezone.now()
    form_processing_time_in_seconds =\
        (audit_end_time - audit_start_time).total_seconds()

    ResultFormStats.objects.get_or_create(
        processing_time=form_processing_time_in_seconds,
        user=request.user.userprofile,
        result_form=result_form,
        approved_by_supervisor=approved_by_supervisor,
        reviewed_by_supervisor=reviewed_by_supervisor)


def audit_action(audit, post_data, result_form, url):
    """Update an audit and result form based on post_date.

    :param audit: The audit to modify.
    :param post_data: The post data to look for strings in.
    :param result_form: The result form to modify.
    :param url: The a default url to return.

    :returns: The url.
    """
    if 'forward' in post_data:
        # forward to supervisor
        audit.reviewed_team = True
        url = 'audit-print'

    if 'return' in post_data:
        # return to audit team
        audit.reviewed_team = False

    if 'implement' in post_data:
        # take implementation action
        audit.reviewed_supervisor = True

        if audit.resolution_recommendation ==\
                AuditResolution.MAKE_AVAILABLE_FOR_ARCHIVE:
            audit.for_superadmin = True
        elif audit.resolution_recommendation ==\
                AuditResolution.SEND_TO_CLEARANCE:
            audit.active = False
            result_form.reject(new_state=FormState.CLEARANCE)
        elif audit.action_prior_to_recommendation in\
                [ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
                 ActionsPrior.REQUEST_COPY_FROM_FIELD]:
            audit.active = True
            audit.reviewed_supervisor = False
        else:
            audit.active = False
            result_form.reject(new_state=FormState.DATA_ENTRY_1)

    audit.save()

    return url


def create_or_get_audit(post_data, user, result_form, form):
    """Get or save an audit for the result form.

    :param post_data: The form data to use in the audit form.
    :param user: The user to assign to the audit as user or supervisor
        depending on the user's group.
    :param result_form: The result form to associate the audit with.
    :param form: The form to create an audit from if one does not exist.

    :returns: A retrived or created audit for the result form.
    """
    audit = result_form.audit

    if audit:
        audit = AuditForm(
            post_data, instance=audit).save(commit=False)

        if groups.AUDIT_CLERK in user.groups.values_list(
                'name', flat=True):
            audit.user = user
        else:
            audit.supervisor = user
    else:
        result_form.audited_count += 1
        result_form.save()

        audit = form.save(commit=False)
        audit.result_form = result_form
        audit.user = user

    return audit


def is_clerk(user):
    return groups.AUDIT_CLERK in user.groups.values_list('name', flat=True)


def forms_for_user(user_is_clerk, tally_id):
    """Return the forms to display based on whether the user is a clerk or not.

    Supervisors and admins can view all unreviewed forms in the Audit state,
    Clerks can only view forms that have not been reviewed by the audit team.

    :param user_is_clerk: True if the user is a Clerk, otherwise False.
    :param tally_id: ID of tally.

    :returns: A list of forms in the audit state for this user's group.
    """
    form_list = ResultForm.objects.filter(
        form_state=FormState.AUDIT, audit__reviewed_supervisor=False,
        audit__active=True, tally__id=tally_id).distinct('barcode')

    if user_is_clerk:
        form_list = form_list.filter(
            form_state=FormState.AUDIT, audit__reviewed_team=False,
            audit__active=True)

    return form_list


class DashboardView(LoginRequiredMixin,
                    GroupRequiredMixin,
                    TallyAccessMixin,
                    ReverseSuccessURLMixin,
                    FormView):
    form_class = AuditForm
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "audit/dashboard.html"
    success_url = 'audit-review'

    def get(self, *args, **kwargs):
        format_ = self.kwargs.get('format')
        tally_id = self.kwargs.get('tally_id')
        user_is_clerk = is_clerk(self.request.user)
        active_tab = self.request.GET.get('tab', 'audit')
        barcode = self.request.GET.get('barcode', '').strip()

        form_list = forms_for_user(user_is_clerk, tally_id)

        if barcode:
            form_list = form_list.filter(barcode__icontains=barcode)

        if format_ == 'csv' and active_tab == 'audit':
            return render_to_csv_response(form_list)

        forms = paging(form_list, self.request, page_kwarg='page_audit')

        recall_requests_qs = WorkflowRequest.objects.filter(
            result_form__tally__id=tally_id,
            request_type=RequestType.RECALL_FROM_ARCHIVE
        ).select_related(
            'result_form', 'requester', 'approver'
        ).order_by('-created_date')

        if barcode:
            recall_requests_qs = recall_requests_qs.filter(
                result_form__barcode__icontains=barcode)

        if format_ == 'csv' and active_tab == 'recalls':
            return render_to_csv_response(recall_requests_qs)

        recall_requests =\
            paging(recall_requests_qs, self.request, page_kwarg='page_recalls')

        context = self.get_context_data(
            forms=forms,
            is_clerk=user_is_clerk,
            tally_id=tally_id,
            recall_requests=recall_requests,
            active_tab=active_tab,
            barcode_query=barcode
        )
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST
        pk = post_data['result_form']

        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.AUDIT)

        self.request.session['result_form'] = result_form.pk

        return redirect(self.success_url, tally_id=tally_id)


class ReviewView(LoginRequiredMixin,
                 GroupRequiredMixin,
                 TallyAccessMixin,
                 ReverseSuccessURLMixin,
                 FormView):
    form_class = AuditForm
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "audit/review.html"
    success_url = 'audit_dashboard'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)

        form_class = self.get_form_class()
        audit = result_form.audit
        form = AuditForm(instance=audit) if audit else self.get_form(
            form_class)
        self.request.session[
            'encoded_result_form_audit_start_time'] =\
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))
        reconciliation_form = ReconForm(data=model_to_dict(
            result_form.reconciliationform
        )) if result_form.reconciliationform else None
        results = result_form_results(result_form)

        return self.render_to_response(self.get_context_data(
            form=form,
            result_form=result_form,
            is_clerk=is_clerk(self.request.user),
            tally_id=tally_id,
            reconciliation_form=reconciliation_form,
            results=results,
        ))

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)

        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.AUDIT)

        if form.is_valid():
            user = self.request.user
            audit = create_or_get_audit(post_data,
                                        user.userprofile,
                                        result_form,
                                        form)
            url = audit_action(audit, post_data, result_form, self.success_url)

            # Track supervisors result form reviewing processing time
            if groups.user_groups(user)[0] in [groups.AUDIT_SUPERVISOR,
                                               groups.SUPER_ADMINISTRATOR,
                                               groups.TALLY_MANAGER]:
                encoded_start_time = self.request.session.get(
                    'encoded_result_form_audit_start_time')
                approved_by_supervisor =\
                    audit.for_superadmin and audit.active
                save_result_form_processing_stats(
                    self.request,
                    encoded_start_time,
                    result_form,
                    approved_by_supervisor,
                    audit.reviewed_supervisor)

            return redirect(url, tally_id=tally_id)
        else:
            return self.render_to_response(
                self.get_context_data(form=form,
                                      result_form=result_form,
                                      tally_id=tally_id))


class PrintCoverView(LoginRequiredMixin,
                     TallyAccessMixin,
                     GroupRequiredMixin,
                     TemplateView):
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "audit/print_cover.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session.get('result_form')

        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.AUDIT)

        # Check if cover printing is enabled for audit
        if not result_form.tally.print_cover_in_audit:
            # If printing is disabled, move directly to next state
            # Track audit clerks result form processing time
            if groups.user_groups(self.request.user)[0] == groups.AUDIT_CLERK:
                encoded_start_time = self.request.session.get(
                    'encoded_result_form_audit_start_time')
                save_result_form_processing_stats(
                    self.request, encoded_start_time, result_form)
            del self.request.session['result_form']
            return redirect('audit_dashboard', tally_id=tally_id)

        problems = result_form.audit.get_problems()

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  username=self.request.user.username,
                                  problems=problems,
                                  tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST

        if 'result_form' in post_data:
            pk = session_matches_post_result_form(post_data, self.request)

            result_form = get_object_or_404(ResultForm,
                                            pk=pk,
                                            tally__id=tally_id)
            form_in_state(result_form, FormState.AUDIT)

            # Track audit clerks result form processing time
            if groups.user_groups(self.request.user)[0] == groups.AUDIT_CLERK:
                encoded_start_time = self.request.session.get(
                    'encoded_result_form_audit_start_time')
                save_result_form_processing_stats(
                    self.request, encoded_start_time, result_form)

            del self.request.session['result_form']

            return redirect('audit_dashboard', tally_id=tally_id)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  tally_id=tally_id))


class CreateAuditView(LoginRequiredMixin,
                      GroupRequiredMixin,
                      TallyAccessMixin,
                      ReverseSuccessURLMixin,
                      FormView):
    form_class = BarcodeForm
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "barcode_verify.html"
    success_url = 'audit_dashboard'

    def get_context_data(self, **kwargs):
        context = super(CreateAuditView, self).get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')
        context['header_text'] = _('Create Audit')
        context['form_action'] = ''

        return context

    def get_initial(self):
        initial = super(CreateAuditView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode'] or\
                form.cleaned_data['barcode_scan']
            result_form = get_object_or_404(ResultForm,
                                            barcode=barcode,
                                            tally__id=tally_id)

            possible_states = [FormState.CORRECTION,
                               FormState.DATA_ENTRY_1,
                               FormState.DATA_ENTRY_2,
                               FormState.QUALITY_CONTROL]

            if groups.SUPER_ADMINISTRATOR in groups.user_groups(
                    self.request.user):
                possible_states.append(FormState.ARCHIVED)

            form = safe_form_in_state(result_form, possible_states, form)

            if form:
                return self.form_invalid(form)

            result_form.reject(new_state=FormState.AUDIT)
            result_form.audited_count += 1
            result_form.save()

            Audit.objects.create(result_form=result_form,
                                 user=self.request.user.userprofile)

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)

class AuditRecallRequestsCsvView(LoginRequiredMixin,
                                 GroupRequiredMixin,
                                 TallyAccessMixin,
                                 View):
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR,
                      groups.TALLY_MANAGER, groups.SUPER_ADMINISTRATOR]

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        recall_requests_qs = WorkflowRequest.objects.filter(
            result_form__tally__id=tally_id,
            request_type=RequestType.RECALL_FROM_ARCHIVE
        ).select_related(
            'result_form__center',
            'result_form__ballot',
            'requester',
            'approver'
        ).order_by('-created_date')

        # Define user-friendly headers in the desired order
        headers = [
            'Request ID',
            'Request Type',
            'Status',
            'Barcode',
            'Center Code',
            'Station Number',
            'Ballot Number',
            'Reason',
            'Request Comment',
            'Requested By',
            'Requested On',
            'Actioned By',
            'Actioned On',
            'Action Comment'
        ]

        # Create the HttpResponse object with CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] =\
            'attachment; filename="recall_requests.csv"'

        writer = csv.writer(response)
        writer.writerow(headers) # Write the header row

        # Write data rows
        for req in recall_requests_qs:
            writer.writerow([
                req.pk,
                req.get_request_type_display(),
                req.get_status_display(),
                req.result_form.barcode,
                req.result_form.center.code\
                    if req.result_form.center else None,
                req.result_form.station_number,
                req.result_form.ballot.number\
                    if req.result_form.ballot else None,
                req.get_request_reason_display(),
                req.request_comment,
                req.requester.username if req.requester else None,
                req.created_date.strftime("%Y-%m-%d %H:%M:%S")\
                    if req.created_date else None,
                req.approver.username if req.approver else None,
                req.resolved_date.strftime("%Y-%m-%d %H:%M:%S")\
                    if req.resolved_date else None,
                req.approval_comment
            ])

        return response
