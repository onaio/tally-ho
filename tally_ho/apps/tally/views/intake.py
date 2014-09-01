import json

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView, TemplateView
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.center_details_form import\
    CenterDetailsForm
from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.time import now
from tally_ho.libs.views.session import session_matches_post_result_form
from tally_ho.libs.views import mixins
from tally_ho.libs.views.form_state import form_in_intake_state,\
    safe_form_in_state, form_in_state
from tally_ho.libs.views.errors import add_generic_error

INTAKEN_MESSAGE = _('Duplicate of a form already entered into system.')


def states_for_form(user, states, result_form):
    if groups.INTAKE_SUPERVISOR in groups.user_groups(user)\
            and result_form.form_state == FormState.DATA_ENTRY_1:
        states.append(FormState.DATA_ENTRY_1)

    return states


class CenterDetailsView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = BarcodeForm
    group_required = [groups.INTAKE_CLERK, groups.INTAKE_SUPERVISOR]
    template_name = "barcode_verify.html"
    success_url = 'check-center-details'
    tally_id = None

    def get_context_data(self, **kwargs):
        context = super(CenterDetailsView, self).get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')
        context['form_action'] = ''
        context['header_text'] = _('Intake')

        return context

    def get_initial(self):
        initial = super(CenterDetailsView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        self.tally_id = kwargs['tally_id']
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode, tally__id=self.tally_id)
            url = self.success_url
            user = self.request.user
            possible_states = states_for_form(
                user, [FormState.INTAKE, FormState.UNSUBMITTED], result_form)

            if groups.INTAKE_SUPERVISOR in groups.user_groups(user) and\
                    result_form.form_state == FormState.DATA_ENTRY_1:
                url = 'intake-printcover'

            form = safe_form_in_state(result_form, possible_states, form)

            if form:
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk

            duplicated_forms = result_form.get_duplicated_forms()
            if duplicated_forms:
                # a form already exists, send to clearance
                self.request.session['intake-error'] = INTAKEN_MESSAGE
                result_form.send_to_clearance()

                for oneDuplicatedForm in duplicated_forms:
                    if oneDuplicatedForm.form_state != FormState.CLEARANCE:
                        oneDuplicatedForm.send_to_clearance()

                return redirect('intake-clearance')

            if result_form.form_state != FormState.DATA_ENTRY_1:
                result_form.form_state = FormState.INTAKE
                result_form.user = user
                result_form.save()

            if result_form.center:
                return redirect(url, tally_id=self.tally_id)
            else:
                return redirect('intake-enter-center', tally_id=self.tally_id)
        else:
            return self.form_invalid(form)


class EnterCenterView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.TallyAccessMixin,
                      mixins.ReverseSuccessURLMixin,
                      FormView):
    form_class = CenterDetailsForm
    group_required = [groups.INTAKE_CLERK, groups.INTAKE_SUPERVISOR]
    template_name = "enter_center_details.html"
    success_url = 'check-center-details'

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        pk = self.request.session.get('result_form')

        context = super(EnterCenterView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['form_action'] = ''
        context['header_text'] = _('Intake')
        context['result_form'] = get_object_or_404(ResultForm, pk=pk,
                                                    tally__id=tally_id)

        return context

    def get_initial(self):
        initial = super(EnterCenterView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        post_data = self.request.POST
        form_class = self.get_form_class()
        center_form = self.get_form(form_class)

        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form = safe_form_in_state(result_form, FormState.INTAKE,
                                  center_form)

        if form:
            return self.form_invalid(form)

        if center_form.is_valid():
            station_number = center_form.cleaned_data.get('station_number')
            center_number = center_form.cleaned_data.get('center_number')
            center = Center.objects.get(code=center_number, tally__id=tally_id)

            # Checks if center ballot number and form ballot number are the
            # same
            is_error = False
            center_sub = center.sub_constituency
            if center_sub:
                is_general = result_form.ballot.number == center.sub_constituency.code
                if not is_general:
                    is_women = center_sub.ballot_women is not None
                    if not is_women or\
                            (is_women and result_form.ballot.number != center_sub.ballot_women.number):
                        is_error = True

            if is_error:
                form = add_generic_error(center_form,
                                         _(u"Ballot number do not match for"
                                           u"center and form"))
                return self.render_to_response(self.get_context_data(
                    form=form, header_text=_('Intake'),
                    result_form=result_form,
                    tally_id=tally_id))

            duplicated_forms = result_form.get_duplicated_forms(center,
                                                                station_number)
            if duplicated_forms:
                result_form.station_number = station_number
                result_form.center = center
                # a form already exists, send to clearance
                self.request.session['intake-error'] = INTAKEN_MESSAGE
                result_form.send_to_clearance()

                for oneDuplicatedForm in duplicated_forms:
                    if oneDuplicatedForm.form_state != FormState.CLEARANCE:
                        oneDuplicatedForm.send_to_clearance()

                return redirect('intake-clearance', tally_id=tally_id)

            self.request.session['station_number'] = station_number
            self.request.session['center_number'] = center_number

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.render_to_response(self.get_context_data(
                form=center_form, header_text=_('Intake'),
                result_form=result_form))


class CheckCenterDetailsView(LoginRequiredMixin,
                             mixins.GroupRequiredMixin,
                             mixins.TallyAccessMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    group_required = [groups.INTAKE_CLERK, groups.INTAKE_SUPERVISOR]
    template_name = "check_center_details.html"
    success_url = "intake-check-center-details"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        tally_id = kwargs['tally_id']

        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)

        # When result form has not center/station assigned.
        if not result_form.center:
            station_number = self.request.session.get('station_number')
            center_number = self.request.session.get('center_number')

            center = Center.objects.get(code=center_number, tally__id=tally_id)

            result_form.station_number = station_number
            result_form.center = center

            self.request.session['station_number'] = station_number
            self.request.session['center_number'] = center_number

        form_in_intake_state(result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  header_text=_('Intake'),
                                  tally_id=tally_id))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        tally_id = self.kwargs['tally_id']
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_intake_state(result_form)
        url = None

        if 'is_match' in post_data:
            # When result form has not center/station assigned.
            if not result_form.center:
                station_number = self.request.session.get('station_number')
                center_number = self.request.session.get('center_number')
                center = Center.objects.get(code=center_number, tally__id=tally_id)

                result_form.station_number = station_number
                result_form.center = center

            if 'station_number' in self.request.session:
                del self.request.session['station_number']
            if 'center_number' in self.request.session:
                del self.request.session['center_number']

            # send to print cover
            url = 'intake-printcover'

        elif 'is_not_match' in post_data:
            # send to clearance
            result_form.form_state = FormState.CLEARANCE
            url = 'intake-clearance'
        else:
            del self.request.session['result_form']
            result_form.form_state = FormState.UNSUBMITTED
            url = 'intake'

        result_form.date_seen = now()
        result_form.save()

        return redirect(url, tally_id=tally_id)


class PrintCoverView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     TemplateView):
    group_required = [groups.INTAKE_CLERK, groups.INTAKE_SUPERVISOR]
    template_name = "intake/print_cover.html"
    printed_url = 'intake-printed'

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        possible_states = states_for_form(self.request.user,
                                          [FormState.INTAKE], result_form)
        form_in_state(result_form, possible_states)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                    printed_url=reverse(self.printed_url, args=(pk,),),
                    tally_id=tally_id))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        tally_id = self.kwargs['tally_id']

        if 'result_form' in post_data:
            pk = session_matches_post_result_form(post_data, self.request)
            result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
            possible_states = states_for_form(self.request.user,
                                              [FormState.INTAKE], result_form)
            form_in_state(result_form, possible_states)
            result_form.form_state = FormState.DATA_ENTRY_1
            result_form.save()

            return redirect('intaken', tally_id=tally_id)

        return self.render_to_response(
            self.get_context_data(result_form=result_form, tally_id=tally_id))


class ClearanceView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.TallyAccessMixin,
                    TemplateView):
    template_name = "intake/clearance.html"
    group_required = [groups.INTAKE_CLERK, groups.INTAKE_SUPERVISOR]

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, [FormState.CLEARANCE])
        del self.request.session['result_form']

        older_duplicated = result_form.get_duplicated_forms().first()
        if older_duplicated:
            result_form = older_duplicated

        error_msg = self.request.session.get('intake-error')

        if error_msg:
            del self.request.session['intake-error']

        return self.render_to_response(
            self.get_context_data(error_msg=error_msg,
                                  result_form=result_form,
                                  tally_id=tally_id))


class ConfirmationView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       TemplateView):
    template_name = "success.html"
    group_required = [groups.INTAKE_CLERK, groups.INTAKE_SUPERVISOR]

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        del self.request.session['result_form']

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  header_text=_('Intake'),
                                  next_step=_('Data Entry 1'),
                                  start_url='intake',
                                  tally_id=tally_id))


class IntakePrintedView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.PrintedResultFormMixin,
                     TemplateView):
    group_required = [groups.INTAKE_CLERK, groups.INTAKE_SUPERVISOR]

    def set_printed(self, result_form):
        result_form.intake_printed = True
        result_form.save()
