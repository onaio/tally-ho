from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView
from django.utils.translation import ugettext as _
from guardian.mixins import LoginRequiredMixin

from tally_system.apps.tally.forms.barcode_form import BarcodeForm
from tally_system.apps.tally.forms.clearance_form import ClearanceForm
from tally_system.apps.tally.forms.new_result_form import NewResultForm
from tally_system.apps.tally.models.clearance import Clearance
from tally_system.apps.tally.models.result_form import ResultForm
from tally_system.libs.models.enums.clearance_resolution import\
    ClearanceResolution
from tally_system.libs.models.enums.form_state import FormState
from tally_system.libs.permissions import groups
from tally_system.libs.utils.time import now
from tally_system.libs.views import mixins
from tally_system.libs.views.form_state import form_in_state,\
    safe_form_in_state
from tally_system.libs.views.pagination import paging
from tally_system.libs.views.session import session_matches_post_result_form


def clearance_action(post_data, clearance, result_form, url):
    if 'forward' in post_data:
        # forward to supervisor
        clearance.reviewed_team = True
        url = 'clearance-print'

    if 'return' in post_data:
        # return to audit team
        clearance.reviewed_team = False
        clearance.reviewed_supervisor = False

    if 'implement' in post_data:
        # take implementation action
        clearance.reviewed_supervisor = True

        if clearance.resolution_recommendation ==\
                ClearanceResolution.RESET_TO_PREINTAKE:
            clearance.active = False
            result_form.form_state = FormState.UNSUBMITTED
            if result_form.is_replacement:
                result_form.center = None
                result_form.station_number = None
            result_form.save()

    clearance.save()

    return url


def get_clearance(result_form, post_data, user, form):
    """Fetch the clearance or build it form the result form and form.

    :param result_form: The form get or create a clearance for.
    :param post_data: The post data to create a clearance form from.
    :param user: The user to assign this clearance to.
    :param form: The form to create a new clearance from.
    """
    clearance = result_form.clearance

    if clearance:
        clearance = ClearanceForm(
            post_data, instance=clearance).save(commit=False)

        if groups.CLEARANCE_CLERK in user.groups.values_list(
                'name', flat=True):
            clearance.user = user
        else:
            clearance.supervisor = user
    else:
        clearance = form.save(commit=False)
        clearance.result_form = result_form
        clearance.user = user

    if groups.CLEARANCE_CLERK in user.groups.values_list('name', flat=True):
        clearance.date_team_modified = now()
    else:
        clearance.date_supervisor_modified = now()

    return clearance


def is_clerk(user):
    return groups.CLEARANCE_CLERK in user.groups.values_list('name', flat=True)


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.ReverseSuccessURLMixin,
                    FormView):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/dashboard.html"
    success_url = 'clearance-review'

    def get(self, *args, **kwargs):
        form_list = ResultForm.objects.filter(form_state=FormState.CLEARANCE)
        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(
            forms=forms, is_clerk=is_clerk(self.request.user)))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = post_data['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.CLEARANCE)
        self.request.session['result_form'] = result_form.pk

        return redirect(self.success_url)


class ReviewView(LoginRequiredMixin,
                 mixins.GroupRequiredMixin,
                 mixins.ReverseSuccessURLMixin,
                 FormView):
    form_class = ClearanceForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/review.html"
    success_url = 'clearance'

    def get(self, *args, **kwargs):
        pk = self.request.session['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_class = self.get_form_class()
        clearance = result_form.clearance
        form = ClearanceForm(instance=clearance) if clearance\
            else self.get_form(form_class)

        return self.render_to_response(self.get_context_data(
            form=form, result_form=result_form,
            is_clerk=is_clerk(self.request.user)))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.CLEARANCE)
        form = self.get_form(form_class)

        if form.is_valid():
            user = self.request.user
            clearance = get_clearance(result_form, post_data, user, form)
            url = clearance_action(post_data, clearance, result_form,
                                   self.success_url)

            return redirect(url)
        else:
            return self.render_to_response(self.get_context_data(form=form,
                                           result_form=result_form))


class PrintCoverView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     TemplateView):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/print_cover.html"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.CLEARANCE)
        problems = result_form.clearance.get_problems()

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  problems=problems))

    def post(self, *args, **kwargs):
        post_data = self.request.POST

        if 'result_form' in post_data:
            pk = session_matches_post_result_form(post_data, self.request)

            result_form = get_object_or_404(ResultForm, pk=pk)
            form_in_state(result_form, FormState.CLEARANCE)
            del self.request.session['result_form']

            return redirect('clearance')

        return self.render_to_response(
            self.get_context_data(result_form=result_form))


class CreateClearanceView(LoginRequiredMixin,
                          mixins.GroupRequiredMixin,
                          FormView):
    form_class = BarcodeForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    success_url = 'clearance'
    template_name = "barcode_verify.html"

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_(
                'Create Clearance')))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            possible_states = [FormState.CORRECTION,
                               FormState.DATA_ENTRY_1,
                               FormState.DATA_ENTRY_2,
                               FormState.INTAKE,
                               FormState.QUALITY_CONTROL,
                               FormState.ARCHIVING,
                               FormState.UNSUBMITTED]

            if groups.SUPER_ADMINISTRATOR in groups.user_groups(
                    self.request.user):
                possible_states.append(FormState.ARCHIVED)

            form = safe_form_in_state(result_form, possible_states, form)

            if form:
                return self.form_invalid(form)

            result_form.reject(FormState.CLEARANCE)
            Clearance.objects.create(result_form=result_form,
                                     user=self.request.user)

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class NewFormView(LoginRequiredMixin,
                  mixins.GroupRequiredMixin,
                  FormView):
    form_class = NewResultForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    success_url = 'clearance'
    template_name = "clearance/new_form.html"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')

        if pk:
            result_form = ResultForm.objects.get(pk=pk)
        else:
            barcode = ResultForm.generate_barcode()
            result_form = ResultForm.objects.create(
                barcode=barcode,
                form_state=FormState.CLEARANCE)
            self.request.session['result_form'] = result_form.pk

        form = NewResultForm(instance=result_form)
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(self.get_context_data(
            form=form, result_form=result_form))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = ResultForm.objects.get(pk=pk)

        if result_form.center or result_form.station_number\
                or result_form.ballot or result_form.office:
            # We are writing a form we should not be, bail out.
            del self.request.session['result_form']
            return redirect('clearance')

        result_form.created_user = self.request.user
        form = NewResultForm(post_data, instance=result_form)

        if form.is_valid():
            form.save()
            del self.request.session['result_form']

            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(
                form=form, result_form=result_form))
