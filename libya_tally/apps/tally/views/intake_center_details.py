from django.views.generic import FormView

from libya_tally.apps.tally import forms
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins


class CenterDetailView(mixins.GroupRequiredMixin, FormView):
    form_class = forms.IntakeBarcodeForm
    group_required = groups.INTAKE_CLERK
    template_name = "tally/center_details.html"
