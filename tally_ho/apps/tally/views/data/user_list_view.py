from django.contrib.auth.models import Group
from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.mixins import (DataTablesMixin, GroupRequiredMixin,
                                        TallyAccessMixin)


class UserListDataView(LoginRequiredMixin,
                       GroupRequiredMixin,
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
            # Tally managers viewing tally-manager list get read-only view
            is_super_admin = groups.is_super_administrator(self.request.user)
            if role == 'tally-manager' and not is_super_admin:
                return ''
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
        elif self.role == 'tally-manager':
            qs = qs.filter(groups__name__exact=groups.TALLY_MANAGER)
        else:
            qs = qs.filter(groups__in=Group.objects.all().exclude(
                name__in=[groups.SUPER_ADMINISTRATOR, groups.TALLY_MANAGER]))

        if tally_id:
            qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(Q(username__icontains=keyword) |
                           Q(email__icontains=keyword) |
                           Q(first_name__icontains=keyword) |
                           Q(last_name__icontains=keyword))

        return qs


class UserListView(LoginRequiredMixin,
                   GroupRequiredMixin,
                   DataTablesMixin,
                   TemplateView):
    group_required = [groups.TALLY_MANAGER, groups.SUPER_ADMINISTRATOR]
    template_name = "data/users.html"

    def get(self, request, *args, **kwargs):
        role = kwargs.get('role', 'user')

        is_admin = role == 'admin'
        is_tally_manager = role == 'tally-manager'

        # Tally managers can view tally-manager list but in read-only mode
        is_super_admin = groups.is_super_administrator(request.user)
        read_only = is_tally_manager and not is_super_admin

        return self.render_to_response(self.get_context_data(
            role=role,
            is_admin=is_admin,
            is_tally_manager=is_tally_manager,
            read_only=read_only,
            remote_url=reverse('user-list-data', kwargs={'role': role}),
            export_file_name='user-list',
            server_side=True,
        ))


class UserTallyListView(LoginRequiredMixin,
                        GroupRequiredMixin,
                        TallyAccessMixin,
                        DataTablesMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/users.html"
    enable_scroll_x = False

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        is_admin = False
        role = 'user'

        return self.render_to_response(self.get_context_data(
            role=role,
            is_admin=is_admin,
            remote_url=reverse('user-tally-list-data',
                               kwargs={'tally_id': tally_id, 'role': role}),
            tally_id=tally_id,
            export_file_name='user-list',
            server_side=True,
        ))


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
