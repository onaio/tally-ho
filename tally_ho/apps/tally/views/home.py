from django.urls import reverse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from guardian.mixins import LoginRequiredMixin

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models import UserProfile


GROUP_URLS = {
    groups.AUDIT_CLERK: "audit",
    groups.AUDIT_SUPERVISOR: "audit",
    groups.CLEARANCE_CLERK: "clearance",
    groups.CLEARANCE_SUPERVISOR: "clearance",
    groups.CORRECTIONS_CLERK: "corrections",
    groups.DATA_ENTRY_1_CLERK: "data-entry",
    groups.DATA_ENTRY_2_CLERK: "data-entry",
    groups.INTAKE_CLERK: "intake",
    groups.INTAKE_SUPERVISOR: "intake",
    groups.QUALITY_CONTROL_CLERK: "quality-control",
    groups.QUALITY_CONTROL_SUPERVISOR: "quality-control",
    groups.SUPER_ADMINISTRATOR: "super-administrator-tallies",
    groups.TALLY_MANAGER: "tally-manager",
}


def permission_denied(request):
    return render(request, 'errors/403.html')


def not_found(request):
    return render(request, 'errors/404.html')


def bad_request(request):
    return render(request, 'errors/400.html')


def server_error(request):
    return render(request, 'errors/500.html')


def suspicious_error(request):
    error_message = request.session.get('error_message')

    if error_message:
        del request.session['error_message']

    return render(request,
                  'errors/suspicious.html',
                  {'error_message': error_message})


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def get_user_role_url(self, user):
        if user.groups.count():
            user_group = user.groups.all()[0]

            kwargs = {}
            if user_group.name not in [groups.TALLY_MANAGER,
                                       groups.SUPER_ADMINISTRATOR]:
                userprofile = UserProfile.objects.get(id=user.id)
                if not userprofile.tally:
                    return reverse('home-no-tally')
                kwargs = {'tally_id': userprofile.tally.id}

            return reverse(GROUP_URLS.get(user_group.name), kwargs=kwargs)

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


class LocaleView(TemplateView):
    def get(self, *args, **kwargs):
        get_data = self.request.GET
        locale = get_data.get('locale')

        if locale:
            self.request.session['locale'] = locale
            self.request.session['django_language'] = locale

        next_url = get_data.get('next', 'home')

        if not len(next_url) or next_url.startswith('locale'):
            next_url = 'home'

        return redirect(next_url)


class NoTallyView(LoginRequiredMixin, TemplateView):
    template_name = "no_tally_assigned.html"
