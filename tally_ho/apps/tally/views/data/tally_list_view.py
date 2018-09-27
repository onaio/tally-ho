from django.views.generic import TemplateView
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.views.pagination import paging


class TallyListDataView(LoginRequiredMixin,
                            mixins.GroupRequiredMixin,
                            mixins.DatatablesDisplayFieldsMixin,
                            DatatablesView):
    group_required = groups.TALLY_MANAGER
    model = Tally
    fields = (
        'id',
        'name',
        'created_date',
        'modified_date',
        'active',
        'active',
    )
    display_fields = (
        ('id', 'id'),
        ('name', 'name'),
        ('created_date', 'created_date'),
        ('modified_date', 'modified_date'),
        ('active', 'administer_button'),
        ('active', 'edit_button'),
    )


class TallyListView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "data/tallies.html"

    def get(self, *args, **kwargs):
        # check cache
        tally_list = Tally.objects.all()
        tallies = paging(tally_list, self.request)

        return self.render_to_response(self.get_context_data(
            tallies=tallies,
            remote_url='tally-list-data'))
