from django.views.generic import TemplateView

from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins


class IntakeClerkView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "tally/intake_clerk.html"


class CenterDetailView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "tally/center_details.html"
