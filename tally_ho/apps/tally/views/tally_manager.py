from django.views.generic import FormView, TemplateView, CreateView
from django.shortcuts import get_object_or_404, redirect

from guardian.mixins import LoginRequiredMixin

from tally_ho.libs.views import mixins
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.management.commands.import_data import import_sub_constituencies_and_ballots, \
        import_centers, import_stations, import_candidates
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.forms.tally_form import TallyForm


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/home.html"

    def get(self, *args, **kwargs):
        group_logins = [g.lower().replace(' ', '_') for g in groups.GROUPS]

        return self.render_to_response(self.get_context_data(
            groups=group_logins))


class CreateTallyView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    FormView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/tally_form.html"
    form_class = TallyForm
    success_url = 'tally-manager'

    def form_valid(self, form):
        tally = Tally.objects.create(name = self.request.POST['name'])

        import time

        before = time.time()

        import_sub_constituencies_and_ballots(tally, self.request.FILES['subconst_file'])

        sub_time = time.time()
        print "Subcontituencies created in %s seconds" % (str(sub_time - before))

        import_centers(tally, self.request.FILES['centers_file'])

        centers_time = time.time()
        print "Centers created in %s seconds" % (str(centers_time - sub_time))

        import_stations(tally, self.request.FILES['stations_file'])

        stations_time = time.time()
        print "Stations created in %s seconds" % (str(stations_time - centers_time))

        import_candidates(tally, self.request.FILES['candidates_file'], self.request.FILES['ballots_order_file'])

        candidates_time = time.time()
        print "Candidates created in %s seconds" % (str(candidates_time - stations_time))

        final = time.time() - before

        print "Final: " + str(final)

        return redirect(self.success_url)
