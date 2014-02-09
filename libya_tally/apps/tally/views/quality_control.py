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


class AbstractQualityControl(object):
    def get_action(self, header_text, race_type):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)

        results = result_form.results.filter(candidate__race_type=race_type,
                                             active=True,
                                             entry_version=EntryVersion.FINAL)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  results=results,
                                  header_text=header_text))

    def post_action(self, field):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)

        if 'correct' in post_data:
            # send to dashboard
            quality_control = result_form.qualitycontrol
            quality_control.__dict__[field] = True
            quality_control.save()

            return redirect(self.success_url)
        elif 'incorrect' in post_data:
            # send to reject page
            quality_control = result_form.qualitycontrol
            quality_control.__dict__[field] = False
            quality_control.active = False
            quality_control.save()

            result_form.reject()

            return redirect('quality-control-reject')
        elif 'abort' in post_data:
            # send to entry
            del self.request.session['result_form']
            quality_control = result_form.qualitycontrol
            quality_control.active = False
            quality_control.save()

            return redirect('quality-control-clerk')

        raise SuspiciousOperation('Missing expected POST data')


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

        return self.render_to_response(
            self.get_context_data(result_form=result_form))

    def post(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        quality_control = result_form.qualitycontrol

        if quality_control.reviews_passed:
            result_form.form_state = FormState.ARCHIVING
            result_form.save()

        del self.request.session['result_form']
        return redirect(self.success_url)


class QualityControlReconciliationView(LoginRequiredMixin,
                                       mixins.GroupRequiredMixin,
                                       mixins.ReverseSuccessURLMixin,
                                       FormView,
                                       AbstractQualityControl):
    group_required = groups.QUALITY_CONTROL_CLERK
    template_name = "tally/quality_control/reconciliation.html"
    success_url = 'quality-control-dashboard'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)
        reconciliation_form = ReconForm(data=model_to_dict(
            result_form.reconciliationform))

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  reconciliation_form=reconciliation_form))

    def post(self, *args, **kwargs):
        return self.post_action('passed_reconciliation')


class QualityControlGeneralView(LoginRequiredMixin,
                                mixins.GroupRequiredMixin,
                                mixins.ReverseSuccessURLMixin,
                                FormView,
                                AbstractQualityControl):
    group_required = groups.QUALITY_CONTROL_CLERK
    template_name = "tally/quality_control/general.html"
    success_url = 'quality-control-dashboard'

    def get(self, *args, **kwargs):
        return self.get_action('General', RaceType.GENERAL)

    def post(self, *args, **kwargs):
        return self.post_action('passed_general')


class QualityControlWomenView(LoginRequiredMixin,
                              mixins.GroupRequiredMixin,
                              mixins.ReverseSuccessURLMixin,
                              FormView,
                              AbstractQualityControl):
    group_required = groups.QUALITY_CONTROL_CLERK
    template_name = "tally/quality_control/general.html"
    success_url = 'quality-control-dashboard'

    def get(self, *args, **kwargs):
        return self.get_action('Women', RaceType.WOMEN)

    def post(self, *args, **kwargs):
        return self.post_action('passed_women')
