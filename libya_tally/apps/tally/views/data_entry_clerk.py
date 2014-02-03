from django.forms.formsets import formset_factory
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from libya_tally.apps.tally.forms.data_entry_center_details_form import\
    DataEntryCenterDetailsForm
from libya_tally.apps.tally.forms.candidate_form import CandidateForm
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.permissions import groups
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_data_entry_state


class CenterDetailsView(mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = DataEntryCenterDetailsForm
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/center_details.html"
    success_url = 'data-entry-check-center-details'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CheckCenterDetailsView(mixins.GroupRequiredMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/check_center_details.html"
    success_url = "result-entry"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_data_entry_state(result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))


class EnterResultsView(mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       FormView):
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/enter_results_view.html"
    success_url = "data-entry-clerk"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_data_entry_state(result_form)
        candidates = result_form.ballot.candidates.order_by('number')
        CandidateFormSet = formset_factory(CandidateForm,
                                           extra=len(candidates))
        formset = CandidateFormSet()

        return self.render_to_response(
            self.get_context_data(formset=formset,
                                  result_form=result_form,
                                  candidates=candidates))

    def post(self, *args, **kwargs):
        pk = self.post_data['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_data_entry_state(result_form)
        candidates = result_form.ballot.candidates.order_by('number')
        CandidateFormSet = formset_factory(CandidateForm,
                                           extra=len(candidates))
        formset = CandidateFormSet(self.post_data)

        if formset.is_valid():
            entry_version = None
            new_state = None

            if result_form.form_state == FormState.DATA_ENTRY_1:
                entry_version = EntryVersion.DATA_ENTRY_1
                new_state = FormState.DATA_ENTRY_2
            else:
                entry_version = EntryVersion.DATA_ENTRY_2
                new_state = FormState.CORRECTIONS

            for i, form in enumerate(formset.ordered_forms):
                votes = form.cleaned_data['votes']
                Result.create(
                    candidate=candidates[i],
                    result_form=result_form,
                    entry_version=entry_version,
                    votes=votes)

            result_form.form_state = new_state
            result_form.save()

            return redirect(self.success_url)
        else:
            return self.formset_invalid(formset)
