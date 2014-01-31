from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic import TemplateView

from guardian.mixins import LoginRequiredMixin

from libya_tally.libs.permissions import groups


GROUP_URLS = {
    groups.DATA_ENTRY_CLERK: 'data-entry-clerk',
    groups.INTAKE_CLERK: 'intake-clerk',
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
