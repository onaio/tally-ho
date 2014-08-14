from django.views.generic import TemplateView
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.views.pagination import paging


class CandidateListDataView(LoginRequiredMixin,
                            mixins.GroupRequiredMixin,
                            mixins.DatatablesDisplayFieldsMixin,
                            DatatablesView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Candidate
    fields = (
        'candidate_id',
        'full_name',
        'order',
        'ballot__number',
        'race_type',
        'modified_date',
        'active',
    )
    display_fields = (
        ('candidate_id', 'candidate_id'),
        ('full_name', 'full_name'),
        ('order', 'order'),
        ('ballot__number', 'ballot_number'),
        ('race_type', 'race_type_name'),
        ('modified_date', 'modified_date'),
        ('active', 'candidate_active'),
    )


class CandidateListView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/candidates.html"

    def get(self, *args, **kwargs):
        # check cache
        candidate_list = Candidate.objects.all()
        candidates = paging(candidate_list, self.request)

        return self.render_to_response(self.get_context_data(
            candidates=candidates,
            remote_url='candidate-list-data'))
