from django.core.exceptions import SuspiciousOperation
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.utils.translation import ugettext as _
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.forms.recon_form import ReconForm
from tally_ho.apps.tally.forms.confirm_reset_form import ConfirmResetForm
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.libs.permissions import groups
from tally_ho.libs.verify.quarantine_checks import check_quarantine
from tally_ho.libs.views.session import session_matches_post_result_form
from tally_ho.libs.views import mixins
from tally_ho.libs.views.form_state import safe_form_in_state,\
    form_in_state


def results_for_race(result_form, race_type):
    """Return the results from this form for this specific race type.

    :param result_form: The result form to return results for.
    :param race_type: The type of results to return, component results of None.

    :returns: A queryset of results for this form and race type.
    """
    results = result_form.results.filter(
        active=True,
        entry_version=EntryVersion.FINAL).order_by('candidate__order')

    if race_type is None:
        results = results.filter(candidate__race_type__gt=RaceType.WOMEN)
    else:
        results = results.filter(candidate__race_type=race_type)

    return results


class QualityControlView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
                         mixins.ReverseSuccessURLMixin,
                         FormView):
    form_class = BarcodeForm
    group_required = [groups.QUALITY_CONTROL_CLERK,
                      groups.QUALITY_CONTROL_SUPERVISOR]
    template_name = "barcode_verify.html"
    success_url = 'quality-control-dashboard'

    def get_context_data(self, **kwargs):
        context = super(QualityControlView, self).get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')
        context['form_action'] = ''
        context['header_text'] = _('Quality Control & Archiving')

        return context

    def get_initial(self):
        initial = super(QualityControlView, self).get_initial()
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
            form = safe_form_in_state(result_form, [FormState.QUALITY_CONTROL,
                                                    FormState.ARCHIVING],
                                      form)

            if form:
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk
            QualityControl.objects.create(result_form=result_form,
                                          user=self.request.user.userprofile)

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)


class QualityControlDashboardView(LoginRequiredMixin,
                                  mixins.GroupRequiredMixin,
                                  mixins.TallyAccessMixin,
                                  mixins.ReverseSuccessURLMixin,
                                  FormView):
    form_class = BarcodeForm
    group_required = [groups.QUALITY_CONTROL_CLERK,
                      groups.QUALITY_CONTROL_SUPERVISOR]
    template_name = "quality_control/dashboard.html"
    success_url = 'quality-control-print'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, [FormState.QUALITY_CONTROL])

        reconciliation_form = ReconForm(data=model_to_dict(
            result_form.reconciliationform
        )) if result_form.reconciliationform else None
        results_component = results_for_race(result_form, None)
        results_general = results_for_race(result_form, RaceType.GENERAL)
        results_women = results_for_race(result_form, RaceType.WOMEN)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  reconciliation_form=reconciliation_form,
                                  results_component=results_component,
                                  results_women=results_women,
                                  results_general=results_general,
                                  tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        quality_control = result_form.qualitycontrol
        url = self.success_url
        ballot = Ballot.objects.get(id=result_form.ballot_id)
        form_ballot_marked_as_released = ballot.available_for_release

        if 'correct' in post_data:
            # send to dashboard
            quality_control.passed_general = True
            quality_control.passed_reconciliation = True
            quality_control.passed_women = True
            result_form.save()

            # run quarantine checks
            check_quarantine(result_form, self.request.user)
        elif 'incorrect' in post_data:
            # send to confirm reject page
            if form_ballot_marked_as_released:
                url = 'quality-control-confirm-reject'
            # send to reject page
            else:
                quality_control.passed_general = False
                quality_control.passed_reconciliation = False
                quality_control.passed_women = False
                quality_control.active = False
                result_form.reject()

                url = 'quality-control-reject'
                del self.request.session['result_form']
        elif 'abort' in post_data:
            # send to entry
            quality_control.active = False

            url = 'quality-control'
            del self.request.session['result_form']
        else:
            raise SuspiciousOperation('Missing expected POST data')

        if not form_ballot_marked_as_released:
            quality_control.save()

        return redirect(url, tally_id=tally_id)


class PrintView(LoginRequiredMixin,
                mixins.GroupRequiredMixin,
                mixins.ReverseSuccessURLMixin,
                FormView):
    form_class = BarcodeForm
    group_required = [groups.QUALITY_CONTROL_CLERK,
                      groups.QUALITY_CONTROL_SUPERVISOR]
    template_name = "quality_control/print_cover.html"
    success_url = 'quality-control-success'

    def get(self, *args, **kwargs):
        """Display print view with a cover for audit if an audit exists
        for the form, otherwise with a cover for archive.
        """
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))

    @transaction.atomic
    def post(self, *args, **kwargs):
        """We arrive here after the cover has been printed and the user
        confirms this with a button click. Fetch form and if form had an audit,
        set it to audit state, otherwise to archived state.
        """
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)
        tally_id = kwargs.get('tally_id')

        result_form.form_state = FormState.AUDIT if result_form.audit else\
            FormState.ARCHIVED
        result_form.save()

        return redirect(self.success_url, tally_id=tally_id)


class ConfirmationView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    template_name = "success.html"
    group_required = [groups.QUALITY_CONTROL_CLERK,
                      groups.QUALITY_CONTROL_SUPERVISOR]

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        del self.request.session['result_form']

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  header_text=_('Quality Control'),
                                  next_step=_('Archiving'),
                                  tally_id=tally_id,
                                  start_url='quality-control'))


class ConfirmFormResetView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.TallyAccessMixin,
                           mixins.ReverseSuccessURLMixin,
                           SuccessMessageMixin,
                           FormView):
    form_class = ConfirmResetForm
    group_required = [groups.QUALITY_CONTROL_CLERK,
                      groups.QUALITY_CONTROL_SUPERVISOR]
    template_name = "quality_control/confirm_form_reset.html"
    success_url = 'quality-control-reject'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        tally_id = kwargs.get('tally_id', None)

        if form.is_valid():
            reject_reason = form.data.get('reject_reason')
            result_form_pk = self.request.session.get('result_form')
            result_form = ResultForm.objects.get(id=result_form_pk)
            quality_control = result_form.qualitycontrol
            quality_control.passed_general = False
            quality_control.passed_reconciliation = False
            quality_control.passed_women = False
            quality_control.active = False
            result_form.reject(reject_reason=reject_reason)
            quality_control.save()

            del self.request.session['result_form']

            return redirect(self.success_url, tally_id=tally_id)
