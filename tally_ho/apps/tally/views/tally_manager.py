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
        process_center_row, process_station_row
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


def import_rows_batch(tally, file_to_parse, file_lines, offset, function):
    elements_processed = 0;

    with file_to_parse as f:
        reader = csv.reader(f)

        count = 0
        for line, row in enumerate(reader):
            if count >= offset and count < (offset + BATCH_BLOCK_SIZE):
                if line != 0:
                    function(tally, row)

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

        subconst_file = 'subcontituencies_' + str(tally.id) + '.csv'
        subconst_file_lines = save_file(self.request.FILES['subconst_file'], subconst_file)

        centers_file = 'centers_' + str(tally.id) + '.csv'
        centers_file_lines = save_file(self.request.FILES['centers_file'], centers_file)

        stations_file = 'stations_' + str(tally.id) + '.csv'
        stations_file_lines = save_file(self.request.FILES['stations_file'], stations_file)

        url_kwargs = {'tally_id': tally.id, 'subconst_file': subconst_file,
                'subconst_file_lines': subconst_file_lines,
                'centers_file': centers_file, 'centers_file_lines': centers_file_lines,
                'stations_file': stations_file, 'stations_file_lines': stations_file_lines}
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

        if currentStep == 1:
            subconst_file = open(UPLOADED_FILES_PATH + kwargs['subconst_file'], 'rU')
            subconst_file_lines = int(kwargs['subconst_file_lines'])

            elements_processed = import_rows_batch(tally, subconst_file, subconst_file_lines, offset, process_sub_constituency_row)

        elif currentStep == 2:
            centers_file = open(UPLOADED_FILES_PATH + kwargs['centers_file'], 'rU')
            centers_file_lines = int(kwargs['centers_file_lines'])

            elements_processed = import_rows_batch(tally, centers_file, centers_file_lines, offset, process_center_row)

        elif currentStep == 3:
            centers_file = open(UPLOADED_FILES_PATH + kwargs['stations_file'], 'rU')
            centers_file_lines = int(kwargs['stations_file_lines'])

            elements_processed = import_rows_batch(tally, centers_file, centers_file_lines, offset, process_station_row)

        return HttpResponse(json.dumps({'status': 'OK', 'elements_processed': elements_processed}), content_type='application/json')
