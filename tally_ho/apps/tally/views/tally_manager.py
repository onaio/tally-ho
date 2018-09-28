import csv
from io import StringIO
import json

from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import (
    FormView,
    TemplateView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from guardian.mixins import LoginRequiredMixin

from tally_ho.libs.views import mixins
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditUserProfileForm,
)
from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditAdminProfileForm,
)
from tally_ho.apps.tally.management.commands.import_data import (
    process_sub_constituency_row,
    process_center_row,
    process_station_row,
    process_candidate_row,
    process_results_form_row,
)
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.forms.tally_form import TallyForm
from tally_ho.apps.tally.forms.tally_files_form import TallyFilesForm
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.sub_constituency import SubConstituency


BATCH_BLOCK_SIZE = 100
UPLOADED_FILES_PATH = 'data/uploaded/'


def save_file(file_uploaded, file_name):
    num_lines = 0

    with open(UPLOADED_FILES_PATH + file_name, 'wb+') as destination:
        for chunk in file_uploaded.chunks():
            destination.write(chunk)

        file_uploaded.seek(0)
        fp = StringIO(file_uploaded.read().decode('utf-8'), newline=None)
        reader = csv.reader(fp, dialect=csv.excel_tab)
        num_lines = sum(1 for line in reader)

    return num_lines


def import_rows_batch(tally,
                      file_to_parse,
                      file_lines,
                      offset,
                      function,
                      **kwargs):
    elements_processed = 0
    id_to_ballot_order = {}
    ballot_file_to_parse = kwargs.get('ballots_order_file', False)

    if ballot_file_to_parse:
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


class EditUserView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.ReverseSuccessURLMixin,
                   SuccessMessageMixin,
                   UpdateView):
    model = UserProfile
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/edit_user_profile.html'
    slug_url_kwarg = 'userId'
    slug_field = 'id'

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        context['is_admin'] = self.object.is_administrator

        return context

    def get_form_class(self):
        if self.object.is_administrator:
            return EditAdminProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        self.object = self.get_object()
        role = 'admin' if self.object.is_administrator else 'user'

        return reverse('user-list', kwargs={'role': role})


class RemoveUserConfirmationView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 mixins.ReverseSuccessURLMixin,
                                 SuccessMessageMixin,
                                 DeleteView):
    model = UserProfile
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/remove_user_confirmation.html'
    slug_url_kwarg = 'userId'
    slug_field = 'id'

    def get_context_data(self, **kwargs):
        context = super(
            RemoveUserConfirmationView, self).get_context_data(**kwargs)
        context['is_admin'] = self.object.is_administrator
        context['all_tallies'] = self.object.administrated_tallies.all()

        return context

    def get_success_url(self):
        role = 'admin' if self.object.is_administrator else 'user'

        return reverse('user-list', kwargs={'role': role})


class CreateUserView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     CreateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/edit_user_profile.html'

    def get_context_data(self, **kwargs):
        role = self.kwargs.get('role', 'user')
        context = super(CreateUserView, self).get_context_data(**kwargs)
        context['is_admin'] = role == 'admin'

        return context

    def get_form_class(self):
        if self.kwargs.get('role', 'user') == 'admin':
            return EditAdminProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        return reverse('user-list',
                       kwargs={'role': self.kwargs.get('role', 'user')})


class CreateTallyView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      CreateView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/tally_form.html"
    form_class = TallyForm
    success_url = 'tally-files-form'

    def get_success_url(self):
        return reverse(self.success_url, kwargs={'tally_id': self.object.id})


class TallyUpdateView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.ReverseSuccessURLMixin,
                      UpdateView):
    template_name = 'tally_manager/tally_form.html'
    group_required = groups.TALLY_MANAGER

    model = Tally
    form_class = TallyForm
    success_url = 'tally-list'

    def get_object(self, queryset=None):
        self.object = Tally.objects.get(id=self.kwargs['tally_id'])
        return self.object

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        context = self.get_context_data(tally_id=self.kwargs['tally_id'],
                                        form=form)

        return self.render_to_response(context)


class TallyRemoveView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.ReverseSuccessURLMixin,
                      DeleteView):
    template_name = 'tally_manager/tally_remove.html'
    group_required = groups.TALLY_MANAGER
    model = Tally
    success_url = 'tally-list'

    def get_object(self, queryset=None):
        self.object = Tally.objects.get(id=self.kwargs['tally_id'])
        return self.object


class TallyFilesFormView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         SuccessMessageMixin,
                         FormView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/tally_files_form.html"
    form_class = TallyFilesForm
    success_url = 'batch-view'

    def get_initial(self):
        initial = super(TallyFilesFormView, self).get_initial()
        initial['tally_id'] = self.kwargs['tally_id']

        return initial

    def form_valid(self, form):
        data = form.cleaned_data
        tally_id = data['tally_id']

        tally = Tally.objects.get(id=tally_id)
        SubConstituency.objects.filter(tally=tally).delete()
        Ballot.objects.filter(tally=tally).delete()
        Center.objects.filter(tally=tally).delete()
        Office.objects.filter(tally=tally).delete()
        Ballot.objects.filter(tally=tally).delete()
        Candidate.objects.filter(tally=tally).delete()
        ResultForm.objects.filter(tally=tally).delete()

        subconst_file = 'subcontituencies_%d.csv' % (tally_id)
        subconst_file_lines = save_file(data['subconst_file'], subconst_file)

        centers_file = 'centers_%d.csv' % (tally_id)
        centers_file_lines = save_file(data['centers_file'], centers_file)

        stations_file = 'stations_%d.csv' % (tally_id)
        stations_file_lines = save_file(data['stations_file'], stations_file)

        candidates_file = 'candidates_%d.csv' % (tally_id)
        candidates_file_lines = save_file(data['candidates_file'],
                                          candidates_file)

        ballots_order_file = 'ballot_order_%d.csv' % (tally_id)
        ballots_order_file_lines = save_file(data['ballots_order_file'],
                                             ballots_order_file)

        result_forms_file = 'result_forms_%d.csv' % (tally_id)
        result_forms_file_lines = save_file(data['result_forms_file'],
                                            result_forms_file)

        url_kwargs = {'tally_id': tally_id,
                      'subconst_file': subconst_file,
                      'subconst_file_lines': subconst_file_lines,
                      'centers_file': centers_file,
                      'centers_file_lines': centers_file_lines,
                      'stations_file': stations_file,
                      'stations_file_lines': stations_file_lines,
                      'candidates_file': candidates_file,
                      'candidates_file_lines': candidates_file_lines,
                      'ballots_order_file': ballots_order_file_lines,
                      'result_forms_file': result_forms_file,
                      'result_forms_file_lines': result_forms_file_lines}

        return HttpResponseRedirect(reverse(self.success_url,
                                            kwargs=url_kwargs))


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
            file_to_parse = open(
                UPLOADED_FILES_PATH + kwargs['subconst_file'], 'rU')
            file_lines = int(kwargs['subconst_file_lines'])

            process_function = process_sub_constituency_row

        elif currentStep == 2:
            file_to_parse = open(
                UPLOADED_FILES_PATH + kwargs['centers_file'], 'rU')
            file_lines = int(kwargs['centers_file_lines'])

            process_function = process_center_row

        elif currentStep == 3:
            file_to_parse = open(
                UPLOADED_FILES_PATH + kwargs['stations_file'], 'rU')
            file_lines = int(kwargs['stations_file_lines'])

            process_function = process_station_row

        elif currentStep == 4:
            file_to_parse = open(
                UPLOADED_FILES_PATH + kwargs['candidates_file'], 'rU')
            file_lines = int(kwargs['candidates_file_lines'])

            ballots_order_file = open(
                UPLOADED_FILES_PATH + kwargs['ballots_order_file'], 'rU')
            process_function = process_candidate_row

        elif currentStep == 5:
            file_to_parse = open(
                UPLOADED_FILES_PATH + kwargs['result_forms_file'], 'rU')
            file_lines = int(kwargs['result_forms_file_lines'])

            process_function = process_results_form_row

        elements_processed = import_rows_batch(
            tally,
            file_to_parse,
            file_lines,
            offset,
            process_function,
            ballots_order_file=ballots_order_file)

        return HttpResponse(json.dumps({
            'status': 'OK',
            'elements_processed': elements_processed}),
                            content_type='application/json')
