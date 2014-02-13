from django.core.exceptions import SuspiciousOperation
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView
from django.utils.translation import ugettext as _
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.forms.barcode_form import\
    BarcodeForm
from libya_tally.apps.tally.forms.recon_form import\
    ReconForm
from libya_tally.apps.tally.models.quality_control import QualityControl
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.permissions import groups
from libya_tally.libs.views.session import session_matches_post_result_form
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import safe_form_in_state, form_in_state


def results_for_race(result_form, race_type):
    if race_type is None:
        results = result_form.results.filter(
            candidate__race_type__gt=RaceType.WOMEN, active=True,
            entry_version=EntryVersion.FINAL).order_by('candidate__order')
    else:
        results = result_form.results.filter(
            candidate__race_type=race_type, active=True,
            entry_version=EntryVersion.FINAL).order_by('candidate__order')

    return results


class QualityControlView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.ReverseSuccessURLMixin,
                         FormView):
    form_class = BarcodeForm
    group_required = groups.QUALITY_CONTROL_CLERK
    template_name = "tally/barcode_verify.html"
    success_url = 'quality-control-dashboard'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_('Quality Control')))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            form = safe_form_in_state(result_form, FormState.QUALITY_CONTROL,
                                      form)

            if form:
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk

            QualityControl.objects.create(result_form=result_form,
                                          user=self.request.user)

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class QualityControlDashboardView(LoginRequiredMixin,
                                  mixins.GroupRequiredMixin,
                                  mixins.ReverseSuccessURLMixin,
                                  FormView):
    group_required = groups.QUALITY_CONTROL_CLERK
    template_name = "tally/quality_control/dashboard.html"
    success_url = 'quality-control-clerk'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)

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
                                  results_general=results_general))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        quality_control = result_form.qualitycontrol
        url = self.success_url

        if 'correct' in post_data:
            # send to dashboard
            quality_control.passed_general = True
            quality_control.passed_reconciliation = True
            quality_control.passed_women = True
            result_form.form_state = FormState.ARCHIVING
            result_form.save()
        elif 'incorrect' in post_data:
            # send to reject page
            quality_control.passed_general = False
            quality_control.passed_reconciliation = False
            quality_control.passed_women = False
            quality_control.active = False
            result_form.reject()

            url = 'quality-control-reject'
        elif 'abort' in post_data:
            # send to entry
            quality_control.active = False

            url = 'quality-control-clerk'
        else:
            raise SuspiciousOperation('Missing expected POST data')

        quality_control.save()
        del self.request.session['result_form']

        return redirect(url)
