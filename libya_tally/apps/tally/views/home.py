from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic import TemplateView

from guardian.mixins import LoginRequiredMixin

from libya_tally.libs.permissions import groups


GROUP_URLS = {
    groups.ADMINISTRATOR: "administrator",
    groups.ARCHIVING_CLERK: "archiving-clerk",
    groups.ARCHIVE_SUPERVISOR: "archive-supervisor",
    groups.AUDIT_CLERK: "audit-clerk",
    groups.AUDIT_SUPERVISOR: "audit-supervisor",
    groups.CLEARANCE_CLERK: "clearance-clerk",
    groups.CLEARANCE_SUPERVISOR: "clearance-supervisor",
    groups.CORRECTIONS_CLERK: "corrections-clerk",
    groups.DATA_ENTRY_CLERK: "data-entry-clerk",
    groups.INTAKE_CLERK: "intake-clerk",
    groups.INTAKE_SUPERVISOR: "intake-supervisor",
    groups.QUALITY_CONTROL_CLERK: "quality-control-clerk",
    groups.SUPER_ADMINISTRATOR: "super-administrator",
}


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "tally/home.html"

    def get_user_role_url(self, user):
        if user.groups.count():
            user_group = user.groups.all()[0]
            return reverse(GROUP_URLS.get(user_group.name))
        return None

    def redirect_user_to_role_view(self):
        user = self.request.user
        redirect_url = self.get_user_role_url(user)
        if redirect_url:
            return redirect(redirect_url)
        return None

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        redirect_response = self.redirect_user_to_role_view()
        if redirect_response:
            return redirect_response
        return super(HomeView, self).dispatch(request, *args, **kwargs)
