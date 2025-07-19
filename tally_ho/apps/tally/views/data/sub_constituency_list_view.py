from django.db.models import F, Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.mixins import (DataTablesMixin, GroupRequiredMixin,
                                        TallyAccessMixin)


class SubConstituencyListDataView(LoginRequiredMixin,
                       GroupRequiredMixin,
                       TallyAccessMixin,
                       BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = SubConstituency
    columns = (
        'code',
        'name',
        'election_level',
        'sub_race',
        'ballot_number',
    )

    def render_column(self, row, column):
        if column == 'election_level':
            return row['election_level']
        if column == 'sub_race':
            return row['sub_race']
        elif column == 'ballot_number':
            return row['ballot_number']
        else:
            return super(SubConstituencyListDataView, self).render_column(
                row, column)


    def filter_queryset(self, qs):
        qs = self.get_initial_queryset()
        tally_id = self.kwargs.get('tally_id')
        keyword = self.request.POST.get('search[value]')

        if tally_id:
            qs = qs.filter(tally__id=tally_id)
        else:
            qs = qs.filter(tally__id=tally_id)

        if keyword:
            qs = qs.filter(Q(name__icontains=keyword)|
                           Q(election_level__icontains=keyword))

        return qs

    def get_initial_queryset(self):
        """Get the initial queryset of SubConstituencies, but flatten the
        results to include one row per SubConstituency per ElectrolRace.
        """
        tally_id = self.kwargs.get('tally_id')
        return SubConstituency.objects.filter(
            tally__id=tally_id).prefetch_related('ballots__electrol_race')\
            .values(
                'code',
                'name',
                'ballots__electrol_race__election_level',
                'ballots__electrol_race__ballot_name',
                'ballots__number',
            ).annotate(
                election_level=F('ballots__electrol_race__election_level'),
                sub_race=F('ballots__electrol_race__ballot_name'),
                ballot_number=F('ballots__number')
            )


class SubConstituencyListView(LoginRequiredMixin,
                     GroupRequiredMixin,
                     TallyAccessMixin,
                     DataTablesMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/sub_cons_list.html"

    def get(self, *args, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        reverse_url = 'sub-cons-list-data'
        report_title = _('Sub Constituencies List')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse(
                reverse_url,
                kwargs=kwargs),
            tally_id=tally_id,
            report_title=report_title))
