from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class TallyListDataView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        BaseDatatableView):
    group_required = groups.TALLY_MANAGER
    model = Tally
    columns = (
        'id',
        'name',
        'created_date',
        'modified_date_formatted',
        'administer',
        'edit',
    )

    def render_column(self, row, column):
        if column == 'administer':
            return row.administer_button
        elif column == 'edit':
            return row.edit_button
        else:
            return super(TallyListDataView, self).render_column(row, column)


class TallyListView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "data/tallies.html"

    def get(self, *args, **kwargs):
        return self.render_to_response(self.get_context_data(
            remote_url='tally-list-data'))
