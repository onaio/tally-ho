from django.contrib.auth.models import Group
from django.db.models import Q
from django.views.generic import TemplateView
from django.urls import reverse
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale
)
from tally_ho.libs.views import mixins


class UserListDataView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       BaseDatatableView):
    group_required = [groups.TALLY_MANAGER, groups.SUPER_ADMINISTRATOR]
    model = UserProfile
    columns = (
        'username',
        'email',
        'first_name',
        'last_name',
        'tally.name',
        'date_joined',
        'edit',
    )

    def render_column(self, row, column):
        role = self.kwargs.get('role', 'user')
        if column == 'date_joined':
            return row.date_joined.strftime('%a, %d %b %Y %H:%M:%S %Z')
        if column == 'edit':
            return row.get_edit_link(role=role)
        else:
            return super(UserListDataView, self).render_column(
                row, column)

    def get(self, request, *args, **kwargs):
        self.role = kwargs.get('role', '')

        return super(UserListDataView, self).get(request, *args, **kwargs)

    def filter_queryset(self, qs):
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.POST.get('search[value]')

        if self.role == 'admin':
            qs = qs.filter(groups__name__exact=groups.SUPER_ADMINISTRATOR)
        else:
            qs = qs.filter(groups__in=Group.objects.all().exclude(
                name__in=[groups.SUPER_ADMINISTRATOR, groups.TALLY_MANAGER]))

        if tally_id:
            qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(Q(username__contains=keyword) |
                           Q(email__contains=keyword) |
                           Q(first_name__contains=keyword) |
                           Q(last_name__contains=keyword))

        return qs


class UserListView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "data/users.html"

    def get(self, *args, **kwargs):
        # check cache
        role = kwargs.get('role', 'user')
        is_admin = role == 'admin'
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            role=role,
            is_admin=is_admin,
            remote_url=reverse('user-list-data', kwargs={'role': role}),
            languageDE=language_de))


class UserTallyListView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/users.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        is_admin = False
        role = 'user'
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            role=role,
            is_admin=is_admin,
            remote_url=reverse('user-tally-list-data',
                               kwargs={'tally_id': tally_id, 'role': role}),
            tally_id=tally_id,
            languageDE=language_de))


class UserTallyListDataView(UserListDataView):
    columns = (
        'username',
        'email',
        'first_name',
        'last_name',
        'edit',
    )

    def render_column(self, row, column):
        role = self.kwargs.get('role', 'user')
        if column == 'edit':
            return row.get_edit_tally_link(role=role)
        else:
            return super(UserTallyListDataView, self).render_column(
                row, column)
