import dateutil.parser
from django.core.serializers.json import json, DjangoJSONEncoder
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext as _
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.forms.clearance_form import ClearanceForm
from tally_ho.apps.tally.models.clearance import Clearance
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.models.enums.clearance_resolution import\
    ClearanceResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.time import now
from tally_ho.libs.views import mixins
from tally_ho.libs.views.form_state import form_in_state,\
    safe_form_in_state
from tally_ho.libs.views.pagination import paging
from tally_ho.libs.views.session import session_matches_post_result_form


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
            result_form.duplicate_reviewed = False
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
    userprofile = user.userprofile

    if clearance:
        clearance = ClearanceForm(
            post_data, instance=clearance).save(commit=False)

        if groups.CLEARANCE_CLERK in user.groups.values_list(
                'name', flat=True):
            clearance.user = userprofile
        else:
            clearance.supervisor = userprofile
    else:
        clearance = form.save(commit=False)
        clearance.result_form = result_form
        clearance.user = userprofile

    if groups.CLEARANCE_CLERK in user.groups.values_list('name', flat=True):
        clearance.date_team_modified = now()
    else:
        clearance.date_supervisor_modified = now()

    return clearance


def is_clerk(user):
    return groups.CLEARANCE_CLERK in user.groups.values_list('name', flat=True)


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.TallyAccessMixin,
                    mixins.ReverseSuccessURLMixin,
                    FormView):
    form_class = ClearanceForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/dashboard.html"
    success_url = 'clearance-review'

    def get(self, *args, **kwargs):
        format_ = kwargs.get('format')
        tally_id = kwargs.get('tally_id')
        form_list = ResultForm.objects.filter(
            form_state=FormState.CLEARANCE, tally__id=tally_id)

        if format_ == 'csv':
            return render_to_csv_response(form_list)

        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(
            forms=forms, is_clerk=is_clerk(self.request.user),
            tally_id=tally_id))

    def post(self, *args, **kwargs):
        self.request.session[
            'encoded_result_form_clearance_start_time'] =\
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST
        pk = post_data['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.CLEARANCE)
        self.request.session['result_form'] = result_form.pk

        return redirect(self.success_url, tally_id=tally_id)


class ReviewView(LoginRequiredMixin,
                 mixins.GroupRequiredMixin,
                 mixins.TallyAccessMixin,
                 mixins.ReverseSuccessURLMixin,
                 FormView):
    form_class = ClearanceForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/review.html"
    success_url = 'clearance'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_class = self.get_form_class()
        clearance = result_form.clearance
        form = ClearanceForm(instance=clearance) if clearance\
            else self.get_form(form_class)

        return self.render_to_response(self.get_context_data(
            form=form, result_form=result_form,
            is_clerk=is_clerk(self.request.user),
            tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        form_class = self.get_form_class()
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.CLEARANCE)
        form = self.get_form(form_class)

        user = self.request.user
        result_form_clearance_start_time =\
            dateutil.parser.parse(self.request.session.get(
                'encoded_result_form_clearance_start_time'))
        del self.request.session['encoded_result_form_clearance_start_time']

        # Track clearance clerks review result form processing time
        ResultFormStats.objects.get_or_create(
            form_state=FormState.CLEARANCE,
            start_time=result_form_clearance_start_time,
            end_time=timezone.now(),
            user=user.userprofile,
            result_form=result_form)

        if form.is_valid():
            clearance = get_clearance(result_form, post_data, user, form)
            url = clearance_action(post_data, clearance, result_form,
                                   self.success_url)

            return redirect(url, tally_id=tally_id)
        else:
            return self.render_to_response(
                self.get_context_data(form=form,
                                      result_form=result_form,
                                      tally_id=tally_id))


class PrintCoverView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/print_cover.html"
    printed_url = 'clearance-printed'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.CLEARANCE)
        problems = result_form.clearance.get_problems()

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  problems=problems,
                                  printed_url=reverse(
                                      self.printed_url, args=(pk,)),
                                  tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST

        if 'result_form' in post_data:
            pk = session_matches_post_result_form(post_data, self.request)

            result_form = get_object_or_404(ResultForm,
                                            pk=pk,
                                            tally__id=tally_id)
            form_in_state(result_form, FormState.CLEARANCE)
            del self.request.session['result_form']

            return redirect('clearance', tally_id=tally_id)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  tally_id=tally_id))


class CreateClearanceView(LoginRequiredMixin,
                          mixins.GroupRequiredMixin,
                          mixins.TallyAccessMixin,
                          FormView):
    form_class = BarcodeForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    success_url = 'clearance-check-center-details'
    template_name = 'barcode_verify.html'

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(CreateClearanceView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['header_text'] = _('Create Clearance')
        context['form_action'] = reverse(self.success_url,
                                         kwargs={'tally_id': tally_id})

        return context

    def get_initial(self):
        initial = super(CreateClearanceView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode'] or\
                        form.cleaned_data['barcode_scan']
            result_form = get_object_or_404(ResultForm,
                                            barcode=barcode,
                                            tally__id=tally_id)

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

            self.request.session['result_form'] = result_form.pk

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)


class CheckCenterDetailsView(LoginRequiredMixin,
                             mixins.GroupRequiredMixin,
                             mixins.TallyAccessMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    form_class = BarcodeForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = 'barcode_verify.html'
    success_url = 'clearance-add'

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        pk = self.request.session.get('result_form')

        context = super(
            CheckCenterDetailsView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['header_text'] = _('Clearance')
        context['form_action'] = reverse(self.success_url,
                                         kwargs={'tally_id': tally_id})
        context['result_form'] = get_object_or_404(ResultForm,
                                                   pk=pk,
                                                   tally__id=tally_id)

        return context

    def get_initial(self):
        initial = super(CheckCenterDetailsView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode'] or\
                        form.cleaned_data['barcode_scan']
            result_form = get_object_or_404(ResultForm,
                                            barcode=barcode,
                                            tally__id=tally_id)

            possible_states = [FormState.CORRECTION,
                               FormState.DATA_ENTRY_1,
                               FormState.DATA_ENTRY_2,
                               FormState.INTAKE,
                               FormState.QUALITY_CONTROL,
                               FormState.UNSUBMITTED]

            if groups.SUPER_ADMINISTRATOR in groups.user_groups(
                    self.request.user):
                possible_states.append(FormState.ARCHIVED)

            form = safe_form_in_state(result_form, possible_states, form)

            if form:
                return self.form_invalid(form)

            self.template_name = 'check_clearance_center_details.html'
            form_action = reverse(self.success_url,
                                  kwargs={'tally_id': tally_id})

            return self.render_to_response(
                self.get_context_data(result_form=result_form,
                                      header_text=_('Create Clearance'),
                                      form_action=form_action,
                                      tally_id=tally_id))
        else:
            return self.form_invalid(form)


class AddClearanceFormView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.TallyAccessMixin,
                           FormView):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    success_url = 'clearance'

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST
        pk = self.request.POST.get('result_form', None)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)

        if 'accept_submit' in post_data:
            result_form.reject(FormState.CLEARANCE)
            Clearance.objects.create(result_form=result_form,
                                     user=self.request.user.userprofile)

        result_form.date_seen = now()
        result_form.save()

        return redirect(self.success_url, tally_id=tally_id)


class ClearancePrintedView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.PrintedResultFormMixin,
                           TemplateView):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]

    def set_printed(self, result_form):
        result_form.clearance_printed = True
        result_form.save()
