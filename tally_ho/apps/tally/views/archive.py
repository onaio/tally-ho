from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView, TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.session import session_matches_post_result_form
from tally_ho.libs.verify.quarantine_checks import quarantine_checks
from tally_ho.libs.views import mixins
from tally_ho.libs.views.form_state import form_in_state


def check_quarantine(result_form, user):
    """Run quarantine checks.  Create an audit with links to the failed
    quarantine checks if any fail.

    :param result_form: The result form to run quarantine checks on.
    :param user: The user to associate with an audit if any checks fail.
    """
    audit = None
    result_form.audit_set.update(active=False)

    if not result_form.skip_quarantine_checks:
        for passed_check, check in quarantine_checks():
            if not passed_check(result_form):
                if not audit:
                    audit = Audit.objects.create(
                        user=user,
                        result_form=result_form)

                audit.quarantine_checks.add(check)

    if audit:
        result_form.audited_count += 1
        result_form.save()


def states_for_form(user, result_form, states=[FormState.ARCHIVING]):
    """Get the possible states for this result_form.

    Archive supervisors can modify archived forms, check the user and see if
    this state should be added.

    :param user: The user to determine form states for.
    :param result_form: The form to check the state of.
    :param states: The initial states a form can be in.

    :returns: A list of states that a form may be in.
    """
    if groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR in groups.user_groups(user)\
            and result_form.form_state == FormState.ARCHIVED:
        states.append(FormState.ARCHIVED)

    return states


class ArchivePrintView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       FormView):
    group_required = [groups.QUALITY_CONTROL_ARCHIVE_CLERK,
                      groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR]
    template_name = "archive/print_cover.html"
    success_url = 'archive-success'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        possible_states = states_for_form(self.request.user, result_form)

        form_in_state(result_form, possible_states)
        check_quarantine(result_form, self.request.user)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))

    @transaction.atomic
    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        possible_states = states_for_form(self.request.user, result_form)
        form_in_state(result_form, possible_states)

        result_form.form_state = FormState.AUDIT if result_form.audit else\
            FormState.ARCHIVED
        result_form.save()

        return redirect(self.success_url)


class ConfirmationView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    template_name = "success.html"
    group_required = [groups.QUALITY_CONTROL_ARCHIVE_CLERK,
                      groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR]

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        next_step = _('Quarantine') if result_form.audit else _('Archive')
        del self.request.session['result_form']

        return self.render_to_response(self.get_context_data(
            result_form=result_form, header_text=_('Quality Control & Archiving'),
            next_step=next_step, start_url='quality-control'))
