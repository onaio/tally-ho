from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import FormView
from django.shortcuts import get_object_or_404, redirect

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state


class ClearanceDashboardView(mixins.GroupRequiredMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    group_required = groups.CLEARANCE_CLERK
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
            forms=forms))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = post_data['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.CLEARANCE)

        self.request.session['result_form'] = result_form.pk

        return redirect(self.success_url)


class ClearanceReviewView(mixins.GroupRequiredMixin,
                          mixins.ReverseSuccessURLMixin,
                          FormView):
    group_required = groups.CLEARANCE_CLERK
    template_name = "tally/clearance/dashboard.html"
    success_url = 'clearance-review'

    def get(self, *args, **kwargs):
        pk = self.request.session['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)

        return self.render_to_response(self.get_context_data(
            result_form=result_form))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = post_data['result_form']
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.CLEARANCE)

        self.request.session['result_form'] = result_form.pk

        return redirect(self.success_url)
