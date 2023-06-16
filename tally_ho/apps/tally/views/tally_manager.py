import csv
from io import StringIO
import json
import logging

from django.contrib.messages.views import SuccessMessageMixin
from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ngettext
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import (
    FormView,
    TemplateView,
    CreateView,
    UpdateView,
    DeleteView,
)
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditAdminProfileForm,
    EditUserProfileForm,
)
from tally_ho.apps.tally.forms.site_info_form import SiteInfoForm
from tally_ho.apps.tally.forms.tally_files_form import TallyFilesForm
from tally_ho.apps.tally.forms.tally_form import TallyForm
from tally_ho.apps.tally.management.commands.import_data import (
    process_sub_constituency_row,
    process_center_row,
    process_station_row,
    process_candidate_row,
    process_results_form_row,
)
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from django.contrib.sites.models import Site
from tally_ho.apps.tally.models.site_info import SiteInfo
from tally_ho.libs.permissions import groups
from tally_ho.libs.views import mixins


BATCH_BLOCK_SIZE = 100
UPLOADED_FILES_PATH = 'data/uploaded/'
STEP_TO_ARGS = {
    1: ['subconst_file',
        'subconst_file_lines',
        process_sub_constituency_row],
    2: ['centers_file',
        'centers_file_lines',
        process_center_row],
    3: ['stations_file',
        'stations_file_lines',
        process_station_row],
    4: ['candidates_file',
        'candidates_file_lines',
        process_candidate_row],
    5: ['result_forms_file',
        'result_forms_file_lines',
        process_results_form_row]
}
FILE_NAMES_PREFIXS = {
    'subconst_file': 'subcontituencies_',
    'centers_file': 'centers_',
    'stations_file': 'stations_',
    'candidates_file': 'candidates_',
    'ballots_order_file': 'ballot_order_',
    'result_forms_file': 'result_forms_',
}
logger = logging.getLogger(__name__)


def delete_all_tally_objects(tally):
    """
    Delete all tally objects.

    :param tally: The tally for filtering objects to delete.
    """
    with transaction.atomic():
        ResultForm.objects.filter(tally=tally).delete()
        Candidate.objects.filter(tally=tally).delete()
        Station.objects.filter(tally=tally).delete()
        Center.objects.filter(tally=tally).delete()
        SubConstituency.objects.filter(tally=tally).delete()
        Ballot.objects.filter(tally=tally).delete()
        Office.objects.filter(tally=tally).delete()


def save_file(file_uploaded, file_name):
    num_lines = 0

    with open(UPLOADED_FILES_PATH + file_name, 'wb+') as destination:
        for chunk in file_uploaded.chunks():
            destination.write(chunk)

        file_uploaded.seek(0)
        fp = StringIO(file_uploaded.read().decode('utf-8'), newline=None)
        try:
            reader = csv.reader(fp, dialect=csv.excel_tab)
            num_lines = sum(1 for _ in reader)
        except csv.Error:
            reader = csv.reader(fp, delimiter='\t', quoting=csv.QUOTE_NONE)
            num_lines = sum(1 for _ in reader)

    return num_lines


def import_rows_batch(tally,
                      file_to_parse,
                      file_lines,
                      offset,
                      function,
                      **kwargs):
    """Import rows for the specific file.
    """
    elements_processed = 0
    id_to_ballot_order = {}
    ballot_file_to_parse = kwargs.get('ballots_order_file', False)
    file_to_parse_name = file_to_parse.name.split(UPLOADED_FILES_PATH)[1]

    subconst_file_name_prefix = FILE_NAMES_PREFIXS['subconst_file']
    subconst_file_name = f'{subconst_file_name_prefix}{tally.id}.csv'
    centers_file_name_prefix = FILE_NAMES_PREFIXS['centers_file']
    centers_file_name = f'{centers_file_name_prefix}{tally.id}.csv'
    stations_file_name_prefix = FILE_NAMES_PREFIXS['stations_file']
    stations_file_name = f'{stations_file_name_prefix}{tally.id}.csv'
    candidates_file_name_prefix = FILE_NAMES_PREFIXS['candidates_file']
    candidates_file_name = f'{candidates_file_name_prefix}{tally.id}.csv'
    result_forms_file_name_prefix = FILE_NAMES_PREFIXS['result_forms_file']
    result_forms_file_name = f'{result_forms_file_name_prefix}{tally.id}.csv'

    if ballot_file_to_parse:
        with ballot_file_to_parse as f:
            reader = csv.reader(f)

            for line, row in enumerate(reader):
                if line == 0 and settings.BALLOT_ORDER_COLUMN_NAMES != row:
                    delete_all_tally_objects(tally)
                    error_message = _(u'Invalid ballot order file')
                    return elements_processed, error_message
                if line != 0:
                    id_, ballot_number = row
                    id_to_ballot_order[id_] = ballot_number

    with file_to_parse as f:
        reader = csv.reader(f)
        count = 0
        check_file_column_names = True
        for line, row in enumerate(reader):
            if line == 0 and check_file_column_names:
                if file_to_parse_name == subconst_file_name and\
                        row != settings.SUB_CONSTITUENCY_COLUMN_NAMES:
                    missing_columns = list(
                        set(settings.SUB_CONSTITUENCY_COLUMN_NAMES) - set(row))
                    delete_all_tally_objects(tally)
                    error_message = ngettext(
                        'Column %(cols)s is missing' +\
                        ' in the sub constituency file',
                        'Columns %(cols)s are missing' +\
                        ' in the sub constituency file',
                        len(missing_columns)
                    ) % {"cols": ', '.join(missing_columns),}
                    return elements_processed, error_message
                elif file_to_parse_name == centers_file_name and\
                        row != settings.CENTER_COLUMN_NAMES:
                    missing_columns = list(
                        set(settings.CENTER_COLUMN_NAMES) - set(row))
                    delete_all_tally_objects(tally)
                    error_message = ngettext(
                        'Column %(cols)s is missing in the centers file',
                        'Columns %(cols)s are missing in the centers file',
                        len(missing_columns)
                    ) % {"cols": ', '.join(missing_columns),}
                    return elements_processed, error_message
                elif file_to_parse_name == stations_file_name and\
                        row != settings.STATION_COLUMN_NAMES:
                    missing_columns = list(
                        set(settings.STATION_COLUMN_NAMES) - set(row))
                    delete_all_tally_objects(tally)
                    error_message = ngettext(
                        'Column %(cols)s is missing in the stations file',
                        'Columns %(cols)s are missing in the stations file',
                        len(missing_columns)
                    ) % {"cols": ', '.join(missing_columns),}
                    return elements_processed, error_message
                elif file_to_parse_name == candidates_file_name and\
                        row != settings.CANDIDATE_COLUMN_NAMES:
                    missing_columns = list(
                        set(settings.CANDIDATE_COLUMN_NAMES) - set(row))
                    delete_all_tally_objects(tally)
                    error_message = ngettext(
                        'Column %(cols)s is missing in the candidates file',
                        'Columns %(cols)s are missing in the candidates file',
                        len(missing_columns)
                    ) % {"cols": ', '.join(missing_columns),}
                    return elements_processed, error_message
                elif file_to_parse_name == result_forms_file_name and\
                        row != settings.RESULT_FORM_COLUMN_NAMES:
                    missing_columns = list(
                        set(settings.RESULT_FORM_COLUMN_NAMES) - set(row))
                    delete_all_tally_objects(tally)
                    error_message = ngettext(
                        'Column %(cols)s is missing in the result form file',
                        'Columns %(cols)s are missing in the result form file',
                        len(missing_columns)
                    ) % {"cols": ', '.join(missing_columns),}
                    return elements_processed, error_message
                else:
                    check_file_column_names = False
            if count >= offset and count < (offset + BATCH_BLOCK_SIZE):
                if line != 0:
                    is_not_empty_row =\
                        any(field.strip() for field in row)
                    if id_to_ballot_order:
                        if is_not_empty_row:
                            try:
                                function(tally, row, id_to_ballot_order)
                            except Exception as e:
                                delete_all_tally_objects(tally)
                                error_message = _(u'{}'.format(str(e)))
                                return elements_processed, error_message
                    else:
                        if is_not_empty_row:
                            try:
                                function(tally, row, logger=logger)
                            except Exception as e:
                                delete_all_tally_objects(tally)
                                error_message = _(u'{}'.format(str(e)))
                                return elements_processed, error_message

                elements_processed += 1
            count += 1

    return elements_processed, None


def process_batch_step(current_step, offset, file_map, tally):
    """Interpret step and map to build arguments for batch
    processing of data.
    """
    ballots_order_file = None

    file_name, file_lines, process_function = STEP_TO_ARGS[current_step]

    if current_step == 4:
        ballots_order_file = open(
            UPLOADED_FILES_PATH + file_map['ballots_order_file'], 'r')

    return import_rows_batch(
        tally,
        open(UPLOADED_FILES_PATH + file_map[file_name], 'r'),
        int(file_map[file_lines]),
        offset,
        process_function,
        ballots_order_file=ballots_order_file)


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/home.html"

    def get(self, *args, **kwargs):
        site_id = getattr(settings, "SITE_ID", None)
        group_logins = [g.lower().replace(' ', '_') for g in groups.GROUPS]

        return self.render_to_response(self.get_context_data(
            groups=group_logins,
            site_id=site_id))


class EditUserView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.ReverseSuccessURLMixin,
                   SuccessMessageMixin,
                   UpdateView):
    model = UserProfile
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/edit_user_profile.html'
    slug_url_kwarg = 'user_id'
    slug_field = 'id'

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        is_admin = self.object.is_administrator
        role = self.kwargs.get('role', 'user')
        tally_id = self.kwargs.get('tally_id')
        context['is_admin'] = is_admin
        context['role'] = role
        context['tally_id'] = tally_id
        url_name = None
        url_param = None
        url_keyword = None

        if tally_id:
            url_name = 'user-tally-list'
            url_param = tally_id
            url_keyword = 'tally_id'
        else:
            url_name = 'user-list'
            url_param = role
            url_keyword = 'role'

        context['url_name'] = url_name
        context['url_param'] = url_param
        self.request.session['url_name'] = url_name
        self.request.session['url_param'] = url_param
        self.request.session['url_keyword'] = url_keyword

        return context

    def get_form_class(self):
        if self.object.is_administrator:
            return EditAdminProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        url_name = None
        url_param = None
        url_keyword = None

        try:
            self.request.session['url_name']
        except KeyError:
            url_name = 'user-tally-list',
            url_param = self.kwargs.get('tally_id')
            url_keyword = 'tally_id'
        else:
            url_name = self.request.session['url_name']
            url_param = self.request.session['url_param']
            url_keyword = self.request.session['url_keyword']

        return reverse(url_name,
                       kwargs={url_keyword: url_param})


class RemoveUserConfirmationView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 mixins.ReverseSuccessURLMixin,
                                 SuccessMessageMixin,
                                 DeleteView):
    model = UserProfile
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/remove_user_confirmation.html'
    slug_url_kwarg = 'user_id'
    slug_field = 'id'

    def get_context_data(self, **kwargs):
        context = super(
            RemoveUserConfirmationView, self).get_context_data(**kwargs)
        context['is_admin'] = self.object.is_administrator
        context['all_tallies'] = self.object.administrated_tallies.all()
        context['role'] = self.kwargs.get('role', 'user')
        context['tally_id'] = self.kwargs.get('tally_id')

        return context

    def get_success_url(self):
        url_name = None
        url_param = None
        url_keyword = None

        try:
            self.request.session['url_name']
        except KeyError:
            url_name = 'user-tally-list',
            url_param = self.kwargs.get('tally_id')
            url_keyword = 'tally_id'
        else:
            url_name = self.request.session['url_name']
            url_param = self.request.session['url_param']
            url_keyword = self.request.session['url_keyword']

        return reverse(url_name,
                       kwargs={url_keyword: url_param})


class CreateUserView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     CreateView):
    group_required = groups.TALLY_MANAGER
    template_name = 'tally_manager/edit_user_profile.html'

    def get_context_data(self, **kwargs):
        role = self.kwargs.get('role', 'user')
        tally_id = self.kwargs.get('tally_id')
        context = super(CreateUserView, self).get_context_data(**kwargs)
        context['is_admin'] = role == 'admin'
        url_name = None
        url_param = None
        url_keyword = None

        if tally_id:
            url_name = 'user-tally-list'
            url_param = tally_id
            url_keyword = 'tally_id'
        else:
            url_name = 'user-list'
            url_param = role
            url_keyword = 'role'

        context['url_name'] = url_name
        context['url_param'] = url_param
        self.request.session['url_name'] = url_name
        self.request.session['url_param'] = url_param
        self.request.session['url_keyword'] = url_keyword

        return context

    def get_form_class(self):
        if self.kwargs.get('role', 'user') == 'admin':
            return EditAdminProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        url_name = None
        url_param = None
        url_keyword = None

        try:
            self.request.session['url_name']
        except KeyError:
            url_name = 'user-tally-list',
            url_param = self.kwargs.get('tally_id')
            url_keyword = 'tally_id'
        else:
            url_name = self.request.session['url_name']
            url_param = self.request.session['url_param']
            url_keyword = self.request.session['url_keyword']

        return reverse(url_name,
                       kwargs={url_keyword: url_param})


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
                      TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'tally_manager/tally_remove.html'

    def get(self, *args, **kwargs):
        tally = Tally.objects.get(id=self.kwargs['tally_id'])

        return self.render_to_response(self.get_context_data(
            tally=tally))

    def post(self, *args, **kwargs):
        tally = Tally.objects.get(id=self.kwargs['tally_id'])
        tally.active = False
        tally.save()

        return redirect("tally-list")


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

        delete_all_tally_objects(tally)

        subconst_file_name_prefix = FILE_NAMES_PREFIXS['subconst_file']
        subconst_file = f'{subconst_file_name_prefix}{tally_id}.csv'
        subconst_file_lines = save_file(data['subconst_file'], subconst_file)

        centers_file_name_prefix = FILE_NAMES_PREFIXS['centers_file']
        centers_file = f'{centers_file_name_prefix}{tally_id}.csv'
        centers_file_lines = save_file(data['centers_file'], centers_file)

        stations_file_name_prefix = FILE_NAMES_PREFIXS['stations_file']
        stations_file = f'{stations_file_name_prefix}{tally_id}.csv'
        stations_file_lines = save_file(data['stations_file'], stations_file)

        candidates_file_name_prefix = FILE_NAMES_PREFIXS['candidates_file']
        candidates_file = f'{candidates_file_name_prefix}{tally_id}.csv'
        candidates_file_lines = save_file(data['candidates_file'],
                                          candidates_file)

        ballots_order_file_name_prefix =\
            FILE_NAMES_PREFIXS['ballots_order_file']
        ballots_order_file =\
            f'{ballots_order_file_name_prefix}{tally_id}.csv'
        ballots_order_file_lines = save_file(data['ballots_order_file'],
                                             ballots_order_file)

        result_forms_file_name_prefix = FILE_NAMES_PREFIXS['result_forms_file']
        result_forms_file = f'{result_forms_file_name_prefix}{tally_id}.csv'
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
                      'ballots_order_file': ballots_order_file,
                      'ballots_order_file_lines': ballots_order_file_lines,
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

    def get_initial(self):
        initial = super(TallyFilesFormView, self).get_initial()
        initial['tally_id'] = self.kwargs['tally_id']

        return initial

    @method_decorator(ensure_csrf_cookie)
    def post(self, request, *args, **kwargs):
        tally = Tally.objects.get(id=kwargs['tally_id'])

        offset = int(request.POST.get('offset', 0))
        current_step = int(request.POST.get('step', 1))

        elements_processed, error_message = process_batch_step(
            current_step, offset, kwargs, tally)

        if error_message:
            return HttpResponse(json.dumps({
                'status': 'Error',
                'error_message': str(error_message)}),
                content_type='application/json')

        return HttpResponse(json.dumps({
            'status': 'OK',
            'elements_processed': elements_processed}),
            content_type='application/json')


class SetUserTimeOutView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.ReverseSuccessURLMixin,
                         SuccessMessageMixin,
                         UpdateView):
    model = SiteInfo
    form_class = SiteInfoForm
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/set_user_timeout.html"
    success_url = 'tally-manager'

    def get_object(self):
        site_id = self.kwargs.get('site_id')

        return get_object_or_404(Site, pk=site_id)

    def get(self, *args, **kwargs):
        user_idle_timeout = None
        self.object = self.get_object()

        try:
            siteinfo = SiteInfo.objects.get(site__pk=self.object.pk)
            user_idle_timeout = siteinfo.user_idle_timeout
        except SiteInfo.DoesNotExist:
            user_idle_timeout = getattr(settings, 'DEFAULT_IDLE_TIMEOUT')

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form,
                                  userIdleTimeout=user_idle_timeout))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            site_info = form.save()

            if isinstance(site_info, SiteInfo):
                self.success_message = _(
                    u"Successfully set user timeout to %(user_idle_timeout)s"
                    u" minutes"
                    % {'user_idle_timeout': site_info.user_idle_timeout})

            return redirect(self.success_url)

        user_idle_timeout = None

        try:
            siteinfo = SiteInfo.objects.get(site__pk=self.object.pk)
            user_idle_timeout = siteinfo.user_idle_timeout
        except SiteInfo.DoesNotExist:
            user_idle_timeout = getattr(settings, 'DEFAULT_IDLE_TIMEOUT')

        return self.render_to_response(
            self.get_context_data(
                form=form, userIdleTimeout=user_idle_timeout))
