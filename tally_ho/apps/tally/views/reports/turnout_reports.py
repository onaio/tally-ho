from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from django.db.models import Q, Sum, F, ExpressionWrapper, IntegerField,\
    Value as V
from django.db.models.functions import Coalesce
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins
from tally_ho.libs.models.enums.entry_version import EntryVersion


class RegionsTurnoutReportView(LoginRequiredMixin,
                               mixins.GroupRequiredMixin,
                               TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'reports/turnout_report.html'

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        regions_turnout_report =\
            ReconciliationForm.objects.get_registrants_and_votes_type().filter(
                result_form__tally__id=tally_id,
                entry_version=EntryVersion.FINAL
            )\
            .annotate(
                name=F('result_form__office__region__name'))\
            .values(
                'name'
            )\
            .annotate(
                number_of_voters_voted=Sum('number_valid_votes'))\
            .annotate(
                total_number_of_registrants=Sum('number_of_registrants'))\
            .annotate(
                total_number_of_ballots_used=Sum(
                    ExpressionWrapper(F('number_valid_votes') +
                                      F('number_cancelled_ballots') +
                                      F('number_unstamped_ballots') +
                                      F('number_invalid_votes'),
                                      output_field=IntegerField())))\
            .annotate(turnout_percentage=ExpressionWrapper(
                V(100) *
                F('total_number_of_ballots_used') /
                F('total_number_of_registrants'),
                output_field=IntegerField()))\
            .annotate(male_voters=Coalesce(
                Sum('number_valid_votes',
                    filter=Q(voters_gender_type=0)),
                V(0)))\
            .annotate(female_voters=Coalesce(
                Sum('number_valid_votes',
                    filter=Q(voters_gender_type=1)),
                V(0)))

        return self.render_to_response(
            self.get_context_data(
                tally_id=tally_id,
                report_name=_(u"Region"),
                turnout_report=regions_turnout_report))

