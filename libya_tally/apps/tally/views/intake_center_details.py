from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView
from django.utils.translation import ugettext as _

from libya_tally.apps.tally import forms
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.models.enums.form_state import FormState


def form_in_intake_state(result_form):

    if result_form.form_state != FormState.INTAKE:
        raise Exception(
            _(u"Result Form not in intake state, form in state '%s'" %
                result_form.form_state_name))

    return True


class ReverseSuccessURLMixin(object):
    def get_success_url(self):
        if self.success_url:
            self.success_url = reverse(self.success_url)
        return super(ReverseSuccessURLMixin, self).get_success_url()


class CenterDetailView(mixins.GroupRequiredMixin,
                       ReverseSuccessURLMixin,
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


class CheckCenterDetailView(mixins.GroupRequiredMixin,
                            ReverseSuccessURLMixin,
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
