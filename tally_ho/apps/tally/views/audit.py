from django.utils.translation import ugettext as _
from django.views.generic import FormView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.audit_form import AuditForm
from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.audit_resolution import\
    AuditResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.views.form_state import form_in_state,\
    safe_form_in_state
from tally_ho.libs.views.pagination import paging
from tally_ho.libs.views.session import session_matches_post_result_form


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
        else:
            new_state=FormState.DATA_ENTRY_1
            audit.active = False
            result_form.reject(new_state=new_state)

    audit.save()

    return url


def create_or_get_audit(post_data, user, result_form, form):
    """Get or save an audit for the result form.

    :param post_data: The form data to use in the audit form.
    :param user: The user to assign to the audit as user or supervisor
        depending on the user's group.
    :param result_form: The result form to associate the audit with.
    :param form: The form to create an audit from if one does not exist.

    :returns: A retrived of created audit for the result form.
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


def forms_for_user(user_is_clerk, tally_id=None):
    """Return the forms to display based on whether the user is a clerk or not.

    Supervisors and admins can view all unreviewed forms in the Audit state,
    Clerks can only view forms that have not been reviewed by the audit team.

    :param user_is_clerk: True if the user is a Clerk, otherwise False.

    :returns: A list of forms in the audit state for this user's group.
    """
    form_list = ResultForm.objects.filter(
        form_state=FormState.AUDIT, audit__reviewed_supervisor=False,
        audit__active=True, tally__id=tally_id)

    if user_is_clerk:
        form_list = form_list.filter(
            form_state=FormState.AUDIT, audit__reviewed_team=False,
            audit__active=True)

    return form_list


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.TallyAccessMixin,
                    mixins.ReverseSuccessURLMixin,
                    FormView):
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "audit/dashboard.html"
    success_url = 'audit-review'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        user_is_clerk = is_clerk(self.request.user)
        form_list = forms_for_user(user_is_clerk, tally_id)
        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(
            forms=forms, is_clerk=user_is_clerk,
            tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST
        pk = post_data['result_form']

        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.AUDIT)

        self.request.session['result_form'] = result_form.pk

        return redirect(self.success_url, tally_id=tally_id)


class ReviewView(LoginRequiredMixin,
                 mixins.GroupRequiredMixin,
                 mixins.TallyAccessMixin,
                 mixins.ReverseSuccessURLMixin,
                 FormView):
    form_class = AuditForm
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "audit/review.html"
    success_url = 'audit'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)

        form_class = self.get_form_class()
        audit = result_form.audit
        form = AuditForm(instance=audit) if audit else self.get_form(
            form_class)

        return self.render_to_response(self.get_context_data(
            form=form, result_form=result_form,
            is_clerk=is_clerk(self.request.user),
            tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id=kwargs.get('tally_id')

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)

        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.AUDIT)

        if form.is_valid():
            user = self.request.user
            audit = create_or_get_audit(post_data, user, result_form, form)
            url = audit_action(audit, post_data, result_form, self.success_url)

            return redirect(url, tally_id=tally_id)
        else:
            return self.render_to_response(self.get_context_data(form=form,
                                           result_form=result_form,
                                           tally_id=tally_id))

        return redirect(self.success_url, tally_id=tally_id)


class PrintCoverView(LoginRequiredMixin,
                     mixins.TallyAccessMixin,
                     mixins.GroupRequiredMixin,
                     TemplateView):
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "audit/print_cover.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session.get('result_form')

        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.AUDIT)

        problems = result_form.audit.get_problems()

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  problems=problems,
                                  tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST

        if 'result_form' in post_data:
            pk = session_matches_post_result_form(post_data, self.request)

            result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
            form_in_state(result_form, FormState.AUDIT)
            del self.request.session['result_form']

            return redirect('audit', tally_id=tally_id)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                tally_id=tally_id))


class CreateAuditView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.TallyAccessMixin,
                      mixins.ReverseSuccessURLMixin,
                      FormView):
    form_class = BarcodeForm
    group_required = [groups.AUDIT_CLERK, groups.AUDIT_SUPERVISOR]
    template_name = "barcode_verify.html"
    success_url = 'audit'

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
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode, tally__id=tally_id)

            possible_states = [FormState.CORRECTION,
                               FormState.DATA_ENTRY_1,
                               FormState.DATA_ENTRY_2,
                               FormState.ARCHIVING,
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
                                 user=self.request.user)

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)
