from django.views.generic import TemplateView

from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.apps.tally.models.station import Station
from libya_tally.libs.permissions import groups
from libya_tally.libs.views import mixins


class DashboardView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/home.html"

    def get(self, *args, **kwargs):
        return self.render_to_response(self.get_context_data())


class CenterListView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/centers.html"

    def get(self, *args, **kwargs):
        stations = Station.objects.all()

        return self.render_to_response(self.get_context_data(
            stations=stations))


class FormListView(mixins.GroupRequiredMixin, TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally/super_admin/forms.html"

    def get(self, *args, **kwargs):
        scs = SubConstituency.objects.all()

        return self.render_to_response(self.get_context_data(
            scs=scs))
