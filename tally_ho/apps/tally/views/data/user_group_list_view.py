from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.user_group import UserGroup
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class UserGroupListDataView(LoginRequiredMixin,
                            mixins.GroupRequiredMixin,
                            mixins.TallyAccessMixin,
                            BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = UserGroup
    columns = (
        'group.name',
        'idle_timeout',
        'edit',
    )

    def filter_queryset(self, qs):
        keyword = self.request.GET.get('search[value]', None)

        if keyword:
            qs = qs.filter(Q(group__name__contains=keyword))
        return qs

    def render_column(self, row, column):
        if column == 'edit':
            return row.get_edit_links
        else:
            return super(UserGroupListDataView, self).render_column(
                row, column)


class UserGroupListView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = UserGroup
    template_name = "data/user_groups.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('user-group-list-data', kwargs=kwargs),
            tally_id=tally_id))
