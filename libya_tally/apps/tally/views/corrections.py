from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from libya_tally.apps.tally.forms.intake_barcode_form import\
    IntakeBarcodeForm
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state


def match_forms(result_form):
    match = False
    return match


class CorrectionView(mixins.GroupRequiredMixin,
                     mixins.ReverseSuccessURLMixin,
                     FormView):
    form_class = IntakeBarcodeForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "tally/corrections.html"
    success_url = 'check-center-details'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)
            form_in_state(result_form, [FormState.CORRECTION])
            forms_match = match_forms(result_form)
            self.request.session['result_form'] = result_form.pk

            if forms_match:
                redirect('corrections-match')
            else:
                redirect('corrections-required')

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)
