from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.forms.formsets import formset_factory
from django.forms.util import ErrorList
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView

from libya_tally.apps.tally.forms.data_entry_center_details_form import\
    DataEntryCenterDetailsForm
from libya_tally.apps.tally.forms.candidate_form import CandidateForm
from libya_tally.apps.tally.forms.candidate_formset import BaseCandidateFormSet
from libya_tally.apps.tally.forms.reconciliation_form import ReconciliationForm
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.utils.common import session_matches_post_result_form
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_data_entry_state


def get_data_entry_number(form_state):
    return 1 if form_state == FormState.DATA_ENTRY_1 else 2


def get_formset_and_candidates(result_form, post_data=None):
    candidates = result_form.ballot.candidates.order_by('order')
    CandidateFormSet = formset_factory(CandidateForm,
                                       extra=len(candidates),
                                       formset=BaseCandidateFormSet)
    formset = CandidateFormSet(post_data) if post_data else CandidateFormSet()
    forms_and_candidates = [
        (f, candidates[i]) for i, f in enumerate(formset)]

    return [formset, forms_and_candidates]


class CenterDetailsView(mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = DataEntryCenterDetailsForm
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/data_entry/center_details.html"
    success_url = 'data-entry-check-center-details'

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            center_number = form.cleaned_data['center_number']
            center = Center.objects.get(code=center_number)
            station_number = form.cleaned_data['station_number']
            result_form = get_object_or_404(
                ResultForm, center=center, station_number=station_number)

            try:
                form_in_data_entry_state(result_form)
            except SuspiciousOperation:
                errors = form._errors.setdefault("__all__", ErrorList())
                errors.append(_(u"Form not in Data Entry"))
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk

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

        data_entry_number = get_data_entry_number(result_form.form_state)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  header_text=_('Data Entry') + ' %s' %
                                  data_entry_number))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_data_entry_state(result_form)

        if 'is_match' in post_data:
            # send to print cover
            return redirect('enter-results')
        elif 'is_not_match' in post_data:
            # send to clearance
            result_form.form_state = FormState.CLEARANCE
            result_form.save()

            return redirect('intake-clearance')

        return redirect('data-entry-check-center-details')


class EnterResultsView(mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       FormView):
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/data_entry/enter_results_view.html"
    success_url = "data-entry-clerk"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_data_entry_state(result_form)
        formset, forms_and_candidates = get_formset_and_candidates(result_form)
        reconciliation_form = ReconciliationForm()
        data_entry_number = get_data_entry_number(result_form.form_state)

        return self.render_to_response(
            self.get_context_data(formset=formset,
                                  forms_and_candidates=forms_and_candidates,
                                  reconciliation_form=reconciliation_form,
                                  result_form=result_form,
                                  data_entry_number=data_entry_number))

    @transaction.atomic
    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_data_entry_state(result_form)
        formset, forms_and_candidates = get_formset_and_candidates(result_form,
                                                                   post_data)
        reconciliation_form = ReconciliationForm(post_data)
        data_entry_number = get_data_entry_number(result_form.form_state)

        candidates = result_form.ballot.candidates.order_by('order')
        CandidateFormSet = formset_factory(CandidateForm,
                                           extra=len(candidates),
                                           formset=BaseCandidateFormSet)
        formset = CandidateFormSet(post_data)

        if reconciliation_form.is_valid() and formset.is_valid():

            entry_version = None
            new_state = None

            if result_form.form_state == FormState.DATA_ENTRY_1:
                entry_version = EntryVersion.DATA_ENTRY_1
                new_state = FormState.DATA_ENTRY_2
            else:
                entry_version = EntryVersion.DATA_ENTRY_2
                new_state = FormState.CORRECTION

            for i, form in enumerate(formset.forms):
                votes = form.cleaned_data['votes']
                Result.objects.create(
                    candidate=candidates[i],
                    result_form=result_form,
                    entry_version=entry_version,
                    votes=votes)

            result_form.form_state = new_state
            result_form.save()

            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(
                formset=formset,
                forms_and_candidates=forms_and_candidates,
                reconciliation_form=reconciliation_form,
                result_form=result_form,
                data_entry_number=data_entry_number))
