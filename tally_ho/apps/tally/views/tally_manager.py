from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.edit import UpdateView, DeleteView, CreateView
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import ugettext_lazy as _

from guardian.mixins import LoginRequiredMixin

from tally_ho.libs.views import mixins
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.forms.edit_user_profile_form import EditUserProfileForm
from tally_ho.apps.tally.forms.edit_user_profile_form import EditAdminProfileForm


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/home.html"

    def get(self, *args, **kwargs):
        group_logins = [g.lower().replace(' ', '_') for g in groups.GROUPS]

        return self.render_to_response(self.get_context_data(
            groups=group_logins))


class EditUserView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.ReverseSuccessURLMixin,
                   SuccessMessageMixin,
                   UpdateView):
    model = UserProfile
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/edit_user_profile.html'
    slug_url_kwarg = 'userId'
    slug_field = 'id'

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        context['is_admin'] = self.object.is_administrator

        return context

    def get_form_class(self):
        if self.object.is_administrator:
            return EditAdminProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        role = 'admin' if self.object.is_administrator else 'user'

        return reverse('user-list', kwargs={'role': role})


class RemoveUserConfirmationView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 mixins.ReverseSuccessURLMixin,
                                 SuccessMessageMixin,
                                 DeleteView):
    model = UserProfile
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/remove_user_confirmation.html'
    slug_url_kwarg = 'userId'
    slug_field = 'id'

    def get_context_data(self, **kwargs):
        context = super(RemoveUserConfirmationView, self).get_context_data(**kwargs)
        context['is_admin'] = self.object.is_administrator
        context['all_tallies'] = self.object.administrated_tallies.all()

        return context

    def get_success_url(self):
        role = 'admin' if self.object.is_administrator else 'user'

        return reverse('user-list', kwargs={'role': role})


class CreateUserView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     CreateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/edit_user_profile.html'

    def get_context_data(self, **kwargs):
        role = self.kwargs.get('role', 'user')
        context = super(CreateUserView, self).get_context_data(**kwargs)
        context['is_admin'] = role == 'admin'

        return context

    def get_form_class(self):
        if self.kwargs.get('role', 'user') == 'admin':
            return EditAdminProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        return reverse('user-list',
                       kwargs={'role': self.kwargs.get('role', 'user')})
