from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class UserListDataView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.DatatablesDisplayFieldsMixin,
                       DatatablesView):
    group_required = groups.TALLY_MANAGER
    model = UserProfile
    fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_active',
    )

    display_fields = (
        ('username', 'username'),
        ('email', 'email'),
        ('first_name', 'first_name'),
        ('last_name', 'last_name'),
        ('is_active', 'get_edit_link'),
    )

    def get(self, request, *args, **kwargs):
        self.role = kwargs.get('role', '')

        return super(UserListDataView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super(UserListDataView, self).get_queryset()

        if self.role == 'admin':
            qs = qs.filter(groups__name__exact=groups.SUPER_ADMINISTRATOR)
        else:
            qs = qs.filter(groups__in=Group.objects.all().exclude(name__in=[groups.SUPER_ADMINISTRATOR, groups.TALLY_MANAGER]))

        return qs

    def render_to_response(self, form, **kwargs):
        '''Render Datatables expected JSON format'''

        page = self.get_page(form)

        data = {
            'iTotalRecords': page.paginator.count,
            'iTotalDisplayRecords': page.paginator.count,
            'sEcho': form.cleaned_data['sEcho'],
            'aaData': self.get_rows(page.object_list),
        }

        return self.json_response(data)


class UserListView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "data/users.html"

    def get(self, *args, **kwargs):
        # check cache
        role = kwargs.get('role', 'user')
        is_admin = role == 'admin'

        return self.render_to_response(self.get_context_data(
               role=role,
               is_admin=is_admin,
               remote_url=reverse('user-list-data', kwargs={'role': role})))
