from django.core.exceptions import SuspiciousOperation
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView
from django.utils.translation import ugettext as _
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.barcode_form import\
    BarcodeForm
from tally_ho.apps.tally.forms.recon_form import\
    ReconForm
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.permissions import groups
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
                         mixins.ReverseSuccessURLMixin,
                         FormView):
    form_class = BarcodeForm
    group_required = [groups.QUALITY_CONTROL_ARCHIVE_CLERK,
                      groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR]
    template_name = "barcode_verify.html"
    success_url = 'quality-control-dashboard'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        form_action = ''

        return self.render_to_response(self.get_context_data(
            form=form, header_text=_('Quality Control & Archiving'),
            form_action=form_action))

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
    group_required = [groups.QUALITY_CONTROL_ARCHIVE_CLERK,
                      groups.QUALITY_CONTROL_ARCHIVE_SUPERVISOR]
    template_name = "quality_control/dashboard.html"
    success_url = 'archive-print'

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

            self.request.session['result_form'] = result_form.pk
        elif 'incorrect' in post_data:
            # send to reject page
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

        quality_control.save()

        return redirect(url)
