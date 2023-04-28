from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django.db.models import Sum, F
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.utils.html import escape
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale
)
from tally_ho.libs.views import mixins


class CandidateVotesListDataView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 mixins.TallyAccessMixin,
                                 BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = Result
    columns = (
        'name',
        'total_votes',
        'ballot_number',
    )
    order_columns = (
        'total_votes',
    )

    def filter_queryset(self, qs):
        result_ids = self.request.session.get(
            'result_ids')

        if result_ids:
            if self.request.session.get(
                    'ballot_report', None):
                self.order_columns = ('ballot_number',)

            qs =\
                qs.filter(pk__in=result_ids)\
                .annotate(
                    name=F('candidate__full_name'),
                    ballot_number=F('candidate__ballot__number'))\
                .values(
                    'name',
                    'ballot_number').annotate(total_votes=Sum('votes'))

        keyword = self.request.GET.get('search[value]', None)

        if keyword:
            qs = qs.filter(Q(name__contains=keyword))
        return qs

    def render_column(self, row, column):
        if column == 'name':
            return escape('{0}'.format(row["name"]))
        elif column == 'total_votes':
            return escape('{0}'.format(row["total_votes"]))
        elif column == 'ballot_number':
            return escape('{0}'.format(row["ballot_number"]))
        else:
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
        language_de = get_datatables_language_de_from_locale(self.request)
        tally_id = kwargs.get('tally_id')
        region_id = kwargs.get('region_id')
        constituency_id = kwargs.get('constituency_id')
        sub_constituency_id = kwargs.get('sub_constituency_id')
        ballot_report = self.request.session.get(
            'ballot_report', None)

        try:
            region_name = region_id and Region.objects.get(
                tally__id=tally_id, id=region_id).name
        except Region.DoesNotExist:
            region_name = None

        try:
            constituency_name =\
                constituency_id and Constituency.objects.get(
                    id=constituency_id,
                    tally__id=tally_id).name
        except Constituency.DoesNotExist:
            constituency_name = None

        try:
            sub_constituency_code =\
                sub_constituency_id and SubConstituency.objects.get(
                    id=sub_constituency_id,
                    tally__id=tally_id).code
        except SubConstituency.DoesNotExist:
            sub_constituency_code = None

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                'candidates-list-by-votes-list-data', kwargs=kwargs),
            tally_id=tally_id,
            region_name=region_name,
            constituency_name=constituency_name,
            sub_constituency_code=sub_constituency_code,
            export_file_name='candidates-list-by-votes',
            ballot_report=ballot_report,
            languageDE=language_de,))
