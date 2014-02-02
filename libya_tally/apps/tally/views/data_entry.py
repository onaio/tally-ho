from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView
from django.utils.translation import ugettext as _

from libya_tally.apps.tally import forms
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.models.enums.form_state import FormState


def check_form_state_data_entry(result_form):
    if not result_form.form_state in [
            FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_1]:
        raise Exception(
            _(u"Result Form not in DATA_ENTRY_1 state, form in state '%s'"
              % result_form.form_state_name))


class ReverseSuccessURLMixin(object):
    def get_success_url(self):
        if self.success_url:
            self.success_url = reverse(self.success_url)
        return super(ReverseSuccessURLMixin, self).get_success_url()


class CenterDetailsView(mixins.GroupRequiredMixin,
                        ReverseSuccessURLMixin,
                        FormView):
    form_class = forms.DataEntryCenterDetailsForm
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/center_details.html"
    success_url = 'check-center-details'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CheckCenterDetailView(mixins.GroupRequiredMixin,
                            ReverseSuccessURLMixin,
                            FormView):
    form_class = forms.IntakeBarcodeForm
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/check_center_details.html"
    success_url = "result-entry"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        check_form_state_data_entry(result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))


class EnterResultsView(mixins.GroupRequiredMixin,
                       ReverseSuccessURLMixin,
                       FormView):
    form_class = forms.IntakeBarcodeForm
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/check_center_details.html"
    success_url = "result-entry"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        check_form_state_data_entry(result_form)
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        check_form_state_data_entry(result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))
