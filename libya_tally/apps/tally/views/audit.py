from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import FormView
from django.shortcuts import get_object_or_404, redirect
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.forms.audit_form import AuditForm
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state
from libya_tally.libs.views.session import session_matches_post_result_form


class AuditDashboardView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.ReverseSuccessURLMixin,
                         FormView):
    group_required = groups.AUDIT_CLERK
    template_name = "tally/audit/dashboard.html"
    success_url = 'audit-review'

    def get(self, *args, **kwargs):
        form_list = ResultForm.objects.filter(form_state=FormState.AUDIT)
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
            forms=forms))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = post_data['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.AUDIT)

        self.request.session['result_form'] = result_form.pk

        return redirect(self.success_url)


class AuditReviewView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.ReverseSuccessURLMixin,
                      FormView):
    form_class = AuditForm
    group_required = groups.AUDIT_CLERK
    template_name = "tally/audit/dashboard.html"
    success_url = 'audit-review'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        pk = self.request.session['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)

        return self.render_to_response(self.get_context_data(
            form=form, result_form=result_form))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.AUDIT)

        if form.is_valid():
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form,
                                           result_form=result_form))

        return redirect(self.success_url)
