from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.forms.formsets import formset_factory
from django.forms.util import ErrorList
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView, TemplateView
from guardian.mixins import LoginRequiredMixin

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
from libya_tally.libs.views import mixins
from libya_tally.libs.views.errors import add_generic_error
from libya_tally.libs.views.form_state import form_in_data_entry_state,\
    safe_form_in_state
from libya_tally.libs.views.session import session_matches_post_result_form


def get_data_entry_number(form_state):
    return 1 if form_state == FormState.DATA_ENTRY_1 else 2


def get_formset_and_candidates(result_form, post_data=None):
    candidates = result_form.ballot.candidates.order_by('race_type', 'order')
    CandidateFormSet = formset_factory(CandidateForm,
                                       extra=len(candidates),
                                       formset=BaseCandidateFormSet)
    formset = CandidateFormSet(post_data) if post_data else CandidateFormSet()
    forms_and_candidates = []

    last_race_type = None
    tabindex = 200
    for i, f in enumerate(formset):
        candidate = candidates[i]
        race_type = candidate.race_type_name if\
            candidate.race_type != last_race_type else None
        last_race_type = candidate.race_type

        f.fields['votes'].widget.attrs['tabindex'] = tabindex
        tabindex += 10

        entry = [race_type, f, candidate]
        forms_and_candidates.append(entry)

    return [formset, forms_and_candidates]


def get_header_text(result_form):
    data_entry_number = get_data_entry_number(result_form.form_state)
    return _('Data Entry') + ' %s' % data_entry_number


def user_is_data_entry_1(user):
    return groups.DATA_ENTRY_1_CLERK in groups.user_groups(user)


def user_is_data_entry_2(user):
    return groups.DATA_ENTRY_2_CLERK in groups.user_groups(user)


def check_group_for_state(result_form, user, form):
    """Ensure only data entry 1 clerk can access forms in data entry 1 state
    and similarly for data entry 2.

    Always allow access for the super administrator.

    :param result_form: The result form to check access to.
    :param user: The user to check group of.
    :param form: The Django form to attach an error to.
    :returns: A form with an error if access denied, else None.
    """

    if groups.SUPER_ADMINISTRATOR in groups.user_groups(user):
        return None

    if ((result_form.form_state == FormState.DATA_ENTRY_1 and
       not user_is_data_entry_1(user)) or
       (result_form.form_state == FormState.DATA_ENTRY_2 and
            not user_is_data_entry_2(user))):
        message = _(u"Return form to %s" % result_form.form_state_name)

        return add_generic_error(form, message)


def check_form_for_center_station(center, station_number, result_form):
    if not result_form in ResultForm.objects.filter(
            center=center, station_number=station_number):
        raise SuspiciousOperation(
            _('Center and station numbers do not match'))


def check_state_and_group(result_form, user, form):
    check_state = safe_form_in_state(
        result_form, [FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_2], form)

    check_group = check_group_for_state(result_form, user, form)

    return check_state or check_group


class DataEntryView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.ReverseSuccessURLMixin,
                    FormView):
    form_class = BarcodeForm
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]
    template_name = "tally/barcode_verify.html"
    success_url = 'data-entry-enter-center-details'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        user = self.request.user

        if user_is_data_entry_1(user):
            entry_type = 1
        elif user_is_data_entry_2(user):
            entry_type = 2
        else:
            entry_type = 'Admin'

        return self.render_to_response(
            self.get_context_data(
                form=form, header_text=_('Data Entry %s') % entry_type))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            check_form = check_state_and_group(
                result_form, self.request.user, form)

            if check_form:
                return self.form_invalid(check_form)

            self.request.session['result_form'] = result_form.pk

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CenterDetailsView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = CenterDetailsForm
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]
    template_name = "tally/enter_center_details.html"
    success_url = 'enter-results'

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
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)

        if form.is_valid():
            check_form = check_state_and_group(
                result_form, self.request.user, form)

            if check_form:
                return self.form_invalid(check_form)

            center_number = form.cleaned_data['center_number']
            center = Center.objects.get(code=center_number)
            station_number = form.cleaned_data['station_number']

            try:
                check_form_for_center_station(center, station_number,
                                              result_form)
            except SuspiciousOperation as e:
                errors = form._errors.setdefault(
                    "__all__", ErrorList())
                errors.append(e.message)

                return self.render_to_response(self.get_context_data(
                    form=form, result_form=result_form))

            check_form = check_state_and_group(
                result_form, self.request.user, form)

            if check_form:
                return self.form_invalid(check_form)

            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form,
                                           result_form=result_form))


class CheckCenterDetailsView(LoginRequiredMixin,
                             mixins.GroupRequiredMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]
    template_name = "tally/enter_center_details.html"
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


class EnterResultsView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       FormView):
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]
    template_name = "tally/data_entry/enter_results_view.html"
    success_url = "data-entry-success"

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

        candidates = result_form.ballot.candidates.order_by('race_type',
                                                            'order')
        CandidateFormSet = formset_factory(CandidateForm,
                                           extra=len(candidates),
                                           formset=BaseCandidateFormSet)
        formset = CandidateFormSet(post_data)

        if recon_form.is_valid() and formset.is_valid():
            check_form = check_state_and_group(
                result_form, self.request.user, recon_form)

            if check_form:
                return self.form_invalid(check_form)

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


class ConfirmationView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    template_name = "tally/success.html"
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        del self.request.session['result_form']

        if result_form.form_state == FormState.DATA_ENTRY_2:
            next_step = _('Data Entry 2')
        else:
            next_step = _('Corrections')

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  header_text=_('Data Entry'),
                                  next_step=next_step,
                                  start_url='data-entry-clerk'))
