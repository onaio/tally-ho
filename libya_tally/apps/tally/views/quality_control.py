from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from libya_tally.apps.tally.forms.intake_barcode_form import\
    IntakeBarcodeForm
from libya_tally.apps.tally.models.quality_control import QualityControl
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state


class QualityControlView(mixins.GroupRequiredMixin,
                         mixins.ReverseSuccessURLMixin,
                         FormView):
    form_class = IntakeBarcodeForm
    group_required = groups.QUALITY_CONTROL_CLERK
    template_name = "tally/quality_control/home.html"
    success_url = 'quality-control-dashboard'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)
            form_in_state(result_form, FormState.QUALITY_CONTROL)
            self.request.session['result_form'] = result_form.pk

            QualityControl.objects.create(result_form=result_form,
                                          user=self.request.user)

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class QualityControlDashBoardView(mixins.GroupRequiredMixin,
                                  mixins.ReverseSuccessURLMixin,
                                  FormView):
    group_required = groups.QUALITY_CONTROL_CLERK
    template_name = "tally/quality_control/dashboard.html"
    success_url = 'quality-control-reject'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)
            form_in_state(result_form, FormState.QUALITY_CONTROL)
            self.request.session['result_form'] = result_form.pk

            QualityControl.objects.create(result_form=result_form,
                                          user=self.request.user)

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)
