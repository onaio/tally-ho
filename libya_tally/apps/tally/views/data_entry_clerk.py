from django.db import transaction
from django.forms.formsets import formset_factory
from django.forms.util import ErrorList
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView

from libya_tally.apps.tally.forms.center_details_form import\
    CenterDetailsForm
from libya_tally.apps.tally.forms.barcode_form import BarcodeForm
from libya_tally.apps.tally.forms.candidate_form import CandidateForm
from libya_tally.apps.tally.forms.candidate_formset import BaseCandidateFormSet
from libya_tally.apps.tally.forms.recon_form import ReconForm
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.utils.common import session_matches_post_result_form
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_data_entry_state,\
    safe_form_in_state


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


def get_header_text(result_form):
    data_entry_number = get_data_entry_number(result_form.form_state)
    return _('Data Entry') + ' %s' % data_entry_number


class DataEntryView(mixins.GroupRequiredMixin,
                    mixins.ReverseSuccessURLMixin,
                    FormView):
    form_class = BarcodeForm
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/barcode_verify.html"
    success_url = 'data-entry-enter-center-details'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_('Data Entry')))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            form = safe_form_in_state(
                result_form, [FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_2],
                form)

            if form:
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CenterDetailsView(mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = CenterDetailsForm
    group_required = groups.DATA_ENTRY_CLERK
    template_name = "tally/enter_center_details.html"
    success_url = 'data-entry-check-center-details'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_data_entry_state(result_form)

        return self.render_to_response(
            self.get_context_data(form=form,
                                  result_form=result_form,
                                  header_text=get_header_text(result_form)))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            center_number = form.cleaned_data['center_number']
            center = Center.objects.get(code=center_number)
            station_number = form.cleaned_data['station_number']
            result_form = get_object_or_404(
                ResultForm, center=center, station_number=station_number)

            check_form = safe_form_in_state(
                result_form, [FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_2],
                form)

            if check_form:
                return self.form_invalid(check_form)

            results = Result.objects.filter(
                result_form=result_form,
                entry_version=EntryVersion.DATA_ENTRY_1)

            if results.count() and results[0].user == self.request.user:
                errors = form._errors.setdefault(
                    "__all__", ErrorList())
                errors.append(_(u"You have already entered this form "
                              "as Data Entry Clerk 1."))

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

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  header_text=get_header_text(result_form)))

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
        reconciliation_form = ReconForm()
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
        recon_form = ReconForm(post_data)
        data_entry_number = get_data_entry_number(result_form.form_state)

        candidates = result_form.ballot.candidates.order_by('order')
        CandidateFormSet = formset_factory(CandidateForm,
                                           extra=len(candidates),
                                           formset=BaseCandidateFormSet)
        formset = CandidateFormSet(post_data)

        if recon_form.is_valid() and formset.is_valid():

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
                    votes=votes,
                    user=self.request.user
                )

            re_form = recon_form.save(commit=False)
            re_form.entry_version = entry_version
            re_form.result_form = result_form
            re_form.save()

            result_form.form_state = new_state
            result_form.save()

            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(
                formset=formset,
                forms_and_candidates=forms_and_candidates,
                reconciliation_form=recon_form,
                result_form=result_form,
                data_entry_number=data_entry_number))
