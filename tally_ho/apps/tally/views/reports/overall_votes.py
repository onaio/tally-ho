from django.views.generic import TemplateView
from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _
from guardian.mixins import LoginRequiredMixin

from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.apps.tally.models.result import Result
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


class OverallVotes(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.TallyAccessMixin,
                   TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "reports/overall_votes.html"

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        field = 'result_form__station_number'
        report_name = _('Station')

        if 'center-overall-votes' in request.build_absolute_uri():
            field = 'result_form__center__code'
            report_name = _('Center')

        qs =\
            Result.objects.filter(active=True,
                                  entry_version=EntryVersion.FINAL,
                                  votes__gt=0,
                                  result_form__tally_id=tally_id)

        qs =\
            qs.values(field)\
            .annotate(
                total_votes_per_station=Sum('votes'))\
            .order_by('-total_votes_per_station')

        return self.render_to_response(self.get_context_data(
            results=qs,
            tally_id=tally_id,
            report_name=report_name))
