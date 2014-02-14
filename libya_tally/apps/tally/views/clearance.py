from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import FormView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.forms.clearance_form import ClearanceForm
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.clearance_resolution import\
    ClearanceResolution
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.utils.time import now
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state
from libya_tally.libs.views.session import session_matches_post_result_form


def is_clerk(user):
    return groups.CLEARANCE_CLERK in user.groups.values_list('name', flat=True)


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.ReverseSuccessURLMixin,
                    FormView):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "tally/clearance/dashboard.html"
    success_url = 'clearance-review'

    def get(self, *args, **kwargs):
        form_list = ResultForm.objects.filter(form_state=FormState.CLEARANCE)
        paginator = Paginator(form_list, 100)
        page = self.request.GET.get('page')

        try:
            forms = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            forms = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page.
            forms = paginator.page(paginator.num_pages)

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
    template_name = "tally/clearance/review.html"
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
        clearance = result_form.clearance
        form = self.get_form(form_class)

        if form.is_valid():
            user = self.request.user
            url = self.success_url

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

            if groups.CLEARANCE_CLERK in user.groups.values_list(
                    'name', flat=True):
                clearance.date_team_modified = now()
            else:
                clearance.date_supervisor_modified = now()

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
                    clearance.for_superadmin = True

            clearance.save()

            return redirect(url)
        else:
            return self.render_to_response(self.get_context_data(form=form,
                                           result_form=result_form))

        return redirect(self.success_url)


class PrintCoverView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     TemplateView):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "tally/clearance/print_cover.html"

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
