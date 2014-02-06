from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView, TemplateView

from libya_tally.apps.tally.forms.center_details_form import\
    CenterDetailsForm
from libya_tally.apps.tally.forms.barcode_form import BarcodeForm
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.utils.common import session_matches_post_result_form
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_intake_state,\
    safe_form_in_state, form_in_state


class CenterDetailsView(mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        FormView):
    form_class = BarcodeForm
    group_required = groups.INTAKE_CLERK
    template_name = "tally/barcode_verify.html"
    success_url = 'check-center-details'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_('Intake')))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            form = safe_form_in_state(
                result_form, [FormState.INTAKE, FormState.UNSUBMITTED],
                form)

            if form:
                return self.form_invalid(form)

            result_form.form_state = FormState.INTAKE
            result_form.user = self.request.user
            result_form.save()
            self.request.session['result_form'] = result_form.pk

            if result_form.center:
                return redirect(self.success_url)
            else:
                return redirect('intake-enter-center')
        else:
            return self.form_invalid(form)


class EnterCenterView(mixins.GroupRequiredMixin,
                      mixins.ReverseSuccessURLMixin,
                      FormView):
    form_class = CenterDetailsForm
    group_required = groups.INTAKE_CLERK
    template_name = "tally/enter_center_details.html"
    success_url = 'check-center-details'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_('Intake'),
                                  result_form=result_form))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        form_class = self.get_form_class()
        center_form = self.get_form(form_class)

        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)

        form = safe_form_in_state(result_form, FormState.INTAKE,
                                  center_form)

        if form:
            return self.form_invalid(form)

        if center_form.is_valid():
            center_number = center_form.cleaned_data.get('center_number')
            station_number = center_form.cleaned_data.get('station_number')
            center = Center.objects.get(code=center_number)
            result_form.center = center
            result_form.station_number = station_number
            result_form.save()

            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(
                form=center_form, header_text=_('Intake'),
                result_form=result_form))


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
            self.get_context_data(result_form=result_form,
                                  header_text=_('Intake')))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_intake_state(result_form)

        if 'is_match' in post_data:
            # send to print cover
            return redirect('intake-printcover')
        elif 'is_not_match' in post_data:
            # send to clearance
            result_form.form_state = FormState.CLEARANCE
            result_form.save()

            return redirect('intake-clearance')
        else:
            result_form.form_state = FormState.UNSUBMITTED
            result_form.save()

            return redirect('intake-clerk')


class PrintCoverView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "tally/intake/print_cover.html"

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)

        form_in_intake_state(result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form))

    def post(self, *args, **kwargs):
        post_data = self.request.POST

        if 'result_form' in post_data:
            pk = session_matches_post_result_form(post_data, self.request)

            result_form = get_object_or_404(ResultForm, pk=pk)
            form_in_intake_state(result_form)
            result_form.form_state = FormState.DATA_ENTRY_1
            result_form.save()
            del self.request.session['result_form']

            return redirect('intaken')

        return self.render_to_response(
            self.get_context_data(result_form=result_form))


class ClearanceView(mixins.GroupRequiredMixin, TemplateView):
    template_name = "tally/intake/clearance.html"
    group_required = groups.INTAKE_CLERK

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CLEARANCE])

        return self.render_to_response(
            self.get_context_data(result_form=result_form))
