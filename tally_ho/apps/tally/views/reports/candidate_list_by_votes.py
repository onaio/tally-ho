from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class CandidateVotesListDataView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 mixins.TallyAccessMixin,
                                 BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Result
    columns = (
        'candidate.full_name',
        'votes'
    )

    def filter_queryset(self, qs):
        result_ids = self.request.session.get(
            'result_ids')

        if result_ids:
            qs =\
                qs.filter(pk__in=result_ids)

        keyword = self.request.GET.get('search[value]', None)

        if keyword:
            qs = qs.filter(Q(candidate__full_name__contains=keyword))
        return qs

    def render_column(self, row, column):
        return super(
            CandidateVotesListDataView, self).render_column(row, column)


class CandidateVotesListView(LoginRequiredMixin,
                             mixins.GroupRequiredMixin,
                             mixins.TallyAccessMixin,
                             TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Result
    template_name = "reports/candidate_list_by_votes.html"

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        region_id = kwargs.get('region_id', None)
        constituency_id = kwargs.get('constituency_id', None)
        sub_constituency_id = kwargs.get('sub_constituency_id', None)

        region_name = None
        constituency_name = None
        sub_constituency_code = None

        if region_id:
            region_name = Region.objects.get(id=region_id).name

        if constituency_id:
            constituency_name = Constituency.objects.get(
                id=constituency_id).name

        if sub_constituency_id:
            sub_constituency_code = SubConstituency.objects.get(
                id=sub_constituency_id).code

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                'candidates-list-by-votes-list-data', kwargs=kwargs),
            tally_id=tally_id,
            region_name=region_name,
            constituency_name=constituency_name,
            sub_constituency_code=sub_constituency_code))
