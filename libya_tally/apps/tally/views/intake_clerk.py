from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView, TemplateView

from libya_tally.apps.tally.forms.intake_barcode_form import\
    IntakeBarcodeForm
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_intake_state, \
    form_in_state


class IntakeClerkView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "tally/intake_clerk.html"


class CenterDetailsView(mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = IntakeBarcodeForm
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
            result_form.user = self.request.user
            result_form.save()
            self.request.session['result_form'] = result_form.pk
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CheckCenterDetailsView(mixins.GroupRequiredMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
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
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_intake_state(result_form)

        if 'result_form' not in post_data:
            raise Exception(_(u"Error: Missing result form!"))
        elif int(post_data['result_form']) != pk:
            raise Exception(
                _(u"Session result_form does not match submitted data."))

        if 'is_match' in post_data:
            # send to print cover
            self.request.session['result_form'] = pk
            return redirect('intake-printcover')
        elif 'is_not_match' in post_data:
            # send to clearance
            result_form.form_state = FormState.CLEARANCE
            result_form.save()

            return redirect('intake-clearance')

        return redirect('check-center-details')


class IntakePrintCoverView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "tally/intake_print_cover.html"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_intake_state(result_form)
        print_success = self.request.session.get('print_success')

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  success=print_success))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        print_success = False

        if 'result_form' in post_data:
            pk = post_data['result_form']
            result_form = get_object_or_404(ResultForm, pk=pk)
            form_in_intake_state(result_form)
            result_form.form_state = FormState.DATA_ENTRY_1
            result_form.save()
            self.request.session['result_form'] = result_form.pk
            self.request.session['print_success'] = True

            return redirect('intake-printcover')

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  success=print_success))


class IntakeClearanceView(mixins.GroupRequiredMixin, TemplateView):
    template_name = "tally/intake_clearance.html"
    group_required = groups.INTAKE_CLERK

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CLEARANCE])

        return self.render_to_response(
            self.get_context_data(result_form=result_form))
