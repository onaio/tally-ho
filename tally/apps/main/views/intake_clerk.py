from django.views.generic import TemplateView

from tally.libs.permissions import groups
from tally.libs.views import mixins


class IntakeClerkView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.INTAKE_CLERK
    template_name = "main/intake_clerk.html"
