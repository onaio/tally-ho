from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.forms.barcode_form import\
    BarcodeForm
from libya_tally.apps.tally.models.audit import Audit
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views.session import session_matches_post_result_form
from libya_tally.libs.verify.quarantine_checks import quarantine_checks
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state, safe_form_in_state


def check_quarantine(result_form, user):
    """Run quarantine checks.  Create an audit with links to the failed
    quarantine checks if any fail.

    :param result_form: The result form to run quarantine checks on.
    """
    for passed_check, check in quarantine_checks():
        audit = None
        if not passed_check(result_form):
            if not audit:
                audit = Audit.get_or_create(
                    user=user,
                    result_form=result_form)

            audit.add(check)


class ArchiveView(LoginRequiredMixin,
                  mixins.GroupRequiredMixin,
                  mixins.ReverseSuccessURLMixin,
                  FormView):
    form_class = BarcodeForm
    group_required = groups.ARCHIVE_CLERK
    template_name = "tally/barcode_verify.html"
    success_url = 'archive-print'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_('Archiving')))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            form = safe_form_in_state(result_form, FormState.ARCHIVING,
                                      form)

            if form:
                return self.form_invalid(form)

            check_quarantine(result_form, self.request.user)

            self.request.session['result_form'] = result_form.pk

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class ArchivePrintView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       FormView):
    group_required = groups.ARCHIVE_CLERK
    template_name = "tally/archive/print_cover.html"
    success_url = 'archive-clerk'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.ARCHIVING)

        if result_form.audit:
            cover_type = _('Quarantined')
            form_state = _('QUARANTINED FORM')
        else:
            cover_type = _('Successful Archive')
            form_state = _('ARCHIVED FORM')

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  cover_type=cover_type,
                                  form_state=form_state))

    @transaction.atomic
    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(
            post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.ARCHIVING)

        result_form.form_state = FormState.AUDIT if result_form.audit else\
            FormState.ARCHIVED
        result_form.save()

        del self.request.session['result_form']

        return redirect(self.success_url)
