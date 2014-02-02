from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView

from libya_tally.apps.tally import forms
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_intake_state


class IntakeClerkView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "tally/intake_clerk.html"


class CenterDetailsView(mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = forms.IntakeBarcodeForm
    group_required = groups.INTAKE_CLERK
    template_name = "tally/center_details.html"
    success_url = 'check-center-details'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)
            result_form.form_state = FormState.INTAKE
            result_form.save()
            self.request.session['result_form'] = result_form.pk
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CheckCenterDetailsView(mixins.GroupRequiredMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    form_class = forms.IntakeBarcodeForm
    group_required = groups.INTAKE_CLERK
    template_name = "tally/check_center_details.html"
    success_url = "intake-check-center-details"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_intake_state(result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))

    def post(self, *args, **kwargs):
        post_data = self.request.POST

        if 'match' in post_data:
            # send to print cover
            pk = post_data['match']
            result_form = get_object_or_404(ResultForm, pk=pk)
            form_in_intake_state(result_form)
            self.request.session['result_form'] = pk

            return redirect('intake-printcover')
        elif 'no_match' in post_data:
            # send to clearance
            pk = post_data['no_match']
            result_form = get_object_or_404(ResultForm, pk=pk)
            result_form.form_state = FormState.CLEARANCE
            result_form.save()

            return redirect('intake-clearance')

        return redirect('intake-check-center-details')


class IntakePrintCoverView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "tally/intake_print_cover.html"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_intake_state(result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        success = False

        if 'result_form' in post_data:
            pk = post_data['result_form']
            result_form = get_object_or_404(ResultForm, pk=pk)
            form_in_intake_state(result_form)
            result_form.form_state = FormState.DATA_ENTRY_1
            result_form.save()
            success = True

        return self.render_to_response(
            self.get_context_data(result_form=result_form, success=success))


class IntakeClearanceView(mixins.GroupRequiredMixin, TemplateView):
    template_name = "tally/intake_clearance.html"
    group_required = groups.INTAKE_CLERK
