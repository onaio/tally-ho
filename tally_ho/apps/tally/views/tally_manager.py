import uuid
import urllib
import json
import csv

from django.views.generic import FormView, TemplateView, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse

from guardian.mixins import LoginRequiredMixin

from tally_ho.libs.views import mixins
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.management.commands.import_data import process_sub_constituency_row, \
        process_center_row, process_station_row, process_candidate_row, process_results_form_row
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.forms.tally_form import TallyForm


BATCH_BLOCK_SIZE = 100
UPLOADED_FILES_PATH = 'data/uploaded/'


def save_file(file_uploaded, file_name):
    num_lines = 0

    with open(UPLOADED_FILES_PATH + file_name, 'wb+') as destination:
        for chunk in file_uploaded.chunks():
            destination.write(chunk)

        reader = csv.reader(file_uploaded)
        num_lines = sum(1 for line in reader)

    return num_lines


def import_rows_batch(tally, file_to_parse, file_lines, offset, function, **kwargs):
    elements_processed = 0;
    id_to_ballot_order = {}

    if kwargs.has_key('ballots_order_file') and kwargs.get('ballots_order_file'):
        ballot_file_to_parse = kwargs.get('ballots_order_file')

        with ballot_file_to_parse as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                id_, ballot_number = row
                id_to_ballot_order[id_] = ballot_number

    with file_to_parse as f:
        reader = csv.reader(f)

        count = 0
        for line, row in enumerate(reader):
            if count >= offset and count < (offset + BATCH_BLOCK_SIZE):
                if line != 0:
                    if not id_to_ballot_order:
                        function(tally, row)
                    else:
                        function(tally, row, id_to_ballot_order)

                elements_processed += 1
            count += 1

    return elements_processed


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
                    SuccessMessageMixin,
                    FormView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/tally_form.html"
    form_class = TallyForm
    success_url = 'batch-view'

    def form_valid(self, form):
        tally = Tally.objects.create(name = self.request.POST['name'])

        subconst_file = 'subcontituencies_%d.csv' % (tally.id)
        subconst_file_lines = save_file(self.request.FILES['subconst_file'], subconst_file)

        centers_file = 'centers_%d.csv' % (tally.id)
        centers_file_lines = save_file(self.request.FILES['centers_file'], centers_file)

        stations_file = 'stations_%d.csv' % (tally.id)
        stations_file_lines = save_file(self.request.FILES['stations_file'], stations_file)

        candidates_file = 'candidates_%d.csv' % (tally.id)
        candidates_file_lines = save_file(self.request.FILES['candidates_file'], candidates_file)

        ballots_order_file = 'ballot_order_%d.csv' % (tally.id)
        ballots_order_file_lines = save_file(self.request.FILES['ballots_order_file'], ballots_order_file)

        result_forms_file = 'result_forms_%d.csv' % (tally.id)
        result_forms_file_lines = save_file(self.request.FILES['result_forms_file'], result_forms_file)

        url_kwargs = {'tally_id': tally.id, 'subconst_file': subconst_file,
                'subconst_file_lines': subconst_file_lines,
                'centers_file': centers_file, 'centers_file_lines': centers_file_lines,
                'stations_file': stations_file, 'stations_file_lines': stations_file_lines,
                'candidates_file': candidates_file, 'candidates_file_lines': candidates_file_lines,
                'ballots_order_file': ballots_order_file,
                'result_forms_file': result_forms_file, 'result_forms_file_lines': result_forms_file_lines}
        return HttpResponseRedirect(reverse(self.success_url, kwargs=url_kwargs))


class BatchView(LoginRequiredMixin,
        mixins.GroupRequiredMixin,
        SuccessMessageMixin,
        TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/batch_progress.html"

    def post(self, request, *args, **kwargs):
        try:
            tally = Tally.objects.get(id=kwargs['tally_id'])
        except Tally.DoesNotExist:
            tally = None

        offset = int(request.POST.get('offset', 0))
        currentStep = int(request.POST.get('step', 1))

        ballots_order_file = None
        if currentStep == 1:
            file_to_parse = open(UPLOADED_FILES_PATH + kwargs['subconst_file'], 'rU')
            file_lines = int(kwargs['subconst_file_lines'])

            process_function = process_sub_constituency_row

        elif currentStep == 2:
            file_to_parse = open(UPLOADED_FILES_PATH + kwargs['centers_file'], 'rU')
            file_lines = int(kwargs['centers_file_lines'])

            process_function = process_center_row

        elif currentStep == 3:
            file_to_parse = open(UPLOADED_FILES_PATH + kwargs['stations_file'], 'rU')
            file_lines = int(kwargs['stations_file_lines'])

            process_function = process_station_row

        elif currentStep == 4:
            file_to_parse = open(UPLOADED_FILES_PATH + kwargs['candidates_file'], 'rU')
            file_lines = int(kwargs['candidates_file_lines'])

            ballots_order_file = open(UPLOADED_FILES_PATH + kwargs['ballots_order_file'], 'rU')
            process_function = process_candidate_row

        elif currentStep == 5:
            file_to_parse = open(UPLOADED_FILES_PATH + kwargs['result_forms_file'], 'rU')
            file_lines = int(kwargs['result_forms_file_lines'])

            process_function = process_results_form_row

        elements_processed = import_rows_batch(tally, file_to_parse, file_lines, offset, process_function, ballots_order_file=ballots_order_file)

        return HttpResponse(json.dumps({'status': 'OK', 'elements_processed': elements_processed}), content_type='application/json')
