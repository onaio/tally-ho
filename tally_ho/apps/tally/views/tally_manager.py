import json
import logging
import time

import duckdb
from celery.result import AsyncResult
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.models import Site
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import (CreateView, DeleteView, FormView,
                                  TemplateView, UpdateView)
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditAdminProfileForm, EditTallyManagerProfileForm, EditUserProfileForm)
from tally_ho.apps.tally.forms.site_info_form import SiteInfoForm
from tally_ho.apps.tally.forms.tally_files_form import TallyFilesForm
from tally_ho.apps.tally.forms.tally_form import TallyForm
from tally_ho.apps.tally.management.commands import \
    import_electrol_races_and_ballots as ierb
from tally_ho.apps.tally.management.commands.asign_ballots_to_sub_cons import \
    async_asign_ballots_to_sub_cons_from_ballots_file
from tally_ho.apps.tally.management.commands.import_candidates import \
    async_import_candidates_from_candidates_file
from tally_ho.apps.tally.management.commands.import_centers import \
    async_import_centers_from_centers_file
from tally_ho.apps.tally.management.commands.import_result_forms import \
    async_import_results_forms_from_result_forms_file
from tally_ho.apps.tally.management.commands.import_stations import \
    async_import_stations_from_stations_file
from tally_ho.apps.tally.management.commands.import_sub_cons_and_cons import \
    async_import_sub_constituencies_and_constituencies_from_sub_cons_file
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.site_info import SiteInfo
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.memcache import MemCache
from tally_ho.libs.utils.numbers import parse_int
from tally_ho.libs.views.mixins import (GroupRequiredMixin,
                                        ReverseSuccessURLMixin)

BATCH_BLOCK_SIZE = 100
UPLOADED_FILES_PATH = "data/uploaded/"
STEP_TO_ARGS = {
    1: [
        "ballots_file",
        "ballots_file_lines",
        ierb.async_import_electrol_races_and_ballots_from_ballots_file,
    ],
    2: [
        "subconst_file",
        "subconst_file_lines",
        async_import_sub_constituencies_and_constituencies_from_sub_cons_file,
    ],
    3: [
        "subconst_ballots_file",
        "subconst_ballots_file_lines",
        async_asign_ballots_to_sub_cons_from_ballots_file,
    ],
    4: [
        "centers_file",
        "centers_file_lines",
        async_import_centers_from_centers_file,
    ],
    5: [
        "stations_file",
        "stations_file_lines",
        async_import_stations_from_stations_file,
    ],
    6: [
        "candidates_file",
        "candidates_file_lines",
        async_import_candidates_from_candidates_file,
    ],
    7: [
        "result_forms_file",
        "result_forms_file_lines",
        async_import_results_forms_from_result_forms_file,
    ],
}
FILE_NAMES_PREFIXS = {
    "ballots_file": "ballots_",
    "subconst_file": "subcontituencies_",
    "subconst_ballots_file": "sub_constituency_ballots_",
    "centers_file": "centers_",
    "stations_file": "stations_",
    "candidates_file": "candidates_",
    "ballots_order_file": "ballot_order_",
    "result_forms_file": "result_forms_",
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
        Constituency.objects.filter(tally=tally).delete()
        Ballot.objects.filter(tally=tally).delete()
        Office.objects.filter(tally=tally).delete()
        Region.objects.filter(tally=tally).delete()
        ElectrolRace.objects.filter(tally=tally).delete()


def save_file(file_uploaded, file_name):
    num_lines = 0
    file_path = UPLOADED_FILES_PATH + file_name
    try:
        with open(file_path, "wb+") as destination:
            for chunk in file_uploaded.chunks():
                destination.write(chunk)
        data = duckdb.from_csv_auto(file_path, header=True).distinct()
        num_lines = data.shape[0]
    except Exception as e:
        msg = f"Failed to read file, error: {e}"
        if logger:
            logger.warning(msg)
        raise Exception(msg)

    return num_lines


def exec_csv_file_import_func(
    tally=None, csv_file_path=None, function=None, **kwargs
):
    """
    Generic function for importing csv file data that just executes the actual
    function for importing the data.

    :param tally: tally queryset.
    :param csv_file_path: path to csv file to be imported.
    :param function: import function.
    :returns: elements_processed, None.
    """
    try:
        step_number = kwargs.get("step_number")
        celery_results = function.delay(
            tally_id=tally.id,
            csv_file_path=csv_file_path,
            step_name=STEP_TO_ARGS[step_number][0],
            step_number=step_number,
            ballot_order_file_path=kwargs.get("ballot_order_file_path"),
        )
        elements_processed = {
            "task_id": celery_results.task_id,
            "status": celery_results.status,
            "result": celery_results.result,
        }
        return elements_processed, None
    except Exception as e:
        delete_all_tally_objects(tally)
        error_message = _("{}".format(str(e)))
        return elements_processed, error_message


def import_rows_batch(tally, file_to_parse, function, current_step):
    """Import rows for the specific file."""

    ballots_order_file_name_prefix = FILE_NAMES_PREFIXS["ballots_order_file"]
    ballots_order_file_name = f"{ballots_order_file_name_prefix}{tally.id}.csv"

    return exec_csv_file_import_func(
        tally=tally,
        csv_file_path=file_to_parse.name,
        function=function,
        step_number=current_step,
        ballot_order_file_path=f"{UPLOADED_FILES_PATH}{ballots_order_file_name}",
    )


def process_batch_step(current_step, file_map, tally):
    """Interpret step and map to build arguments for batch
    processing of data.
    """
    file_name, _, process_function = STEP_TO_ARGS[current_step]

    return import_rows_batch(
        tally,
        open(UPLOADED_FILES_PATH + file_map[file_name], "r"),
        process_function,
        current_step,
    )


class DashboardView(
    LoginRequiredMixin, GroupRequiredMixin, TemplateView
):
    group_required = [groups.TALLY_MANAGER, groups.SUPER_ADMINISTRATOR]
    template_name = "tally_manager/home.html"

    def get(self, request, *args, **kwargs):
        site_id = getattr(settings, "SITE_ID", None)
        group_logins = [g.lower().replace(" ", "_") for g in groups.GROUPS]
        is_super_admin = request.user.groups.filter(
            name=groups.SUPER_ADMINISTRATOR).exists()

        return self.render_to_response(
            self.get_context_data(
                groups=group_logins,
                site_id=site_id,
                is_super_admin=is_super_admin,
                tally_id=None)
        )


class EditUserView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = UserProfile
    group_required = [groups.TALLY_MANAGER, groups.SUPER_ADMINISTRATOR]
    template_name = "tally_manager/edit_user_profile.html"
    slug_url_kwarg = "user_id"
    slug_field = "id"

    def dispatch(self, request, *args, **kwargs):
        role = kwargs.get("role", "user")
        # Only SUPER_ADMINISTRATOR can edit tally-manager users
        if role == "tally-manager":
            if not request.user.groups.filter(
                    name=groups.SUPER_ADMINISTRATOR).exists():
                raise PermissionDenied
        return super(EditUserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        is_admin = self.object.is_administrator
        is_tally_manager = self.object.is_tally_manager
        role = self.kwargs.get("role", "user")
        tally_id = self.kwargs.get("tally_id")
        context["is_admin"] = is_admin
        context["is_tally_manager"] = is_tally_manager
        context["role"] = role
        context["tally_id"] = tally_id
        context["object"] = self.object
        context["user_id"] = self.request.user.id
        url_name = None
        url_param = None
        url_keyword = None

        if tally_id:
            url_name = "user-tally-list"
            url_param = tally_id
            url_keyword = "tally_id"
        else:
            url_name = "user-list"
            url_param = role
            url_keyword = "role"

        context["url_name"] = url_name
        context["url_param"] = url_param
        self.request.session["url_name"] = url_name
        self.request.session["url_param"] = url_param
        self.request.session["url_keyword"] = url_keyword

        return context

    def get_form_class(self):
        if self.object.is_administrator:
            return EditAdminProfileForm
        elif self.object.is_tally_manager:
            return EditTallyManagerProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        url_name = None
        url_param = None
        url_keyword = None

        try:
            self.request.session["url_name"]
        except KeyError:
            url_name = ("user-tally-list",)
            url_param = self.kwargs.get("tally_id")
            url_keyword = "tally_id"
        else:
            url_name = self.request.session["url_name"]
            url_param = self.request.session["url_param"]
            url_keyword = self.request.session["url_keyword"]

        return reverse(url_name, kwargs={url_keyword: url_param})


class RemoveUserConfirmationView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = UserProfile
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/remove_user_confirmation.html"
    slug_url_kwarg = "user_id"
    slug_field = "id"

    def get_context_data(self, **kwargs):
        context = super(RemoveUserConfirmationView, self).get_context_data(
            **kwargs
        )
        context["is_admin"] = self.object.is_administrator
        context["all_tallies"] = self.object.administrated_tallies.all()
        context["role"] = self.kwargs.get("role", "user")
        context["tally_id"] = self.kwargs.get("tally_id")

        return context

    def get_success_url(self):
        url_name = None
        url_param = None
        url_keyword = None

        try:
            self.request.session["url_name"]
        except KeyError:
            url_name = ("user-tally-list",)
            url_param = self.kwargs.get("tally_id")
            url_keyword = "tally_id"
        else:
            url_name = self.request.session["url_name"]
            url_param = self.request.session["url_param"]
            url_keyword = self.request.session["url_keyword"]

        return reverse(url_name, kwargs={url_keyword: url_param})


class CreateUserView(
    LoginRequiredMixin, GroupRequiredMixin, CreateView
):
    group_required = [groups.TALLY_MANAGER, groups.SUPER_ADMINISTRATOR]
    template_name = "tally_manager/edit_user_profile.html"

    def dispatch(self, request, *args, **kwargs):
        role = kwargs.get("role", "user")
        # Only SUPER_ADMINISTRATOR can create tally-manager users
        if role == "tally-manager":
            if not request.user.groups.filter(
                    name=groups.SUPER_ADMINISTRATOR).exists():
                raise PermissionDenied
        return super(CreateUserView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        role = self.kwargs.get("role", "user")
        tally_id = self.kwargs.get("tally_id")
        context = super(CreateUserView, self).get_context_data(**kwargs)
        context["is_admin"] = role == "admin"
        context["is_tally_manager"] = role == "tally-manager"
        context["tally_id"] = tally_id
        url_name = None
        url_param = None
        url_keyword = None

        if tally_id:
            url_name = "user-tally-list"
            url_param = tally_id
            url_keyword = "tally_id"
        else:
            url_name = "user-list"
            url_param = role
            url_keyword = "role"

        context["url_name"] = url_name
        context["url_param"] = url_param
        self.request.session["url_name"] = url_name
        self.request.session["url_param"] = url_param
        self.request.session["url_keyword"] = url_keyword
        context["object"] = self.object
        context["user_id"] = self.request.user.id

        return context

    def get_form_class(self):
        role = self.kwargs.get("role", "user")
        if role == "admin":
            return EditAdminProfileForm
        elif role == "tally-manager":
            return EditTallyManagerProfileForm
        else:
            return EditUserProfileForm

    def get_success_url(self):
        url_name = None
        url_param = None
        url_keyword = None

        try:
            self.request.session["url_name"]
        except KeyError:
            url_name = ("user-tally-list",)
            url_param = self.kwargs.get("tally_id")
            url_keyword = "tally_id"
        else:
            url_name = self.request.session["url_name"]
            url_param = self.request.session["url_param"]
            url_keyword = self.request.session["url_keyword"]

        return reverse(url_name, kwargs={url_keyword: url_param})


class CreateTallyView(
    LoginRequiredMixin, GroupRequiredMixin, CreateView
):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/tally_form.html"
    form_class = TallyForm
    success_url = "tally-files-form"

    def get_success_url(self):
        return reverse(self.success_url, kwargs={"tally_id": self.object.id})


class TallyUpdateView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    UpdateView,
):
    template_name = "tally_manager/tally_form.html"
    group_required = groups.TALLY_MANAGER

    model = Tally
    form_class = TallyForm
    success_url = "tally-list"

    def get_object(self, queryset=None):
        self.object = Tally.objects.get(id=self.kwargs["tally_id"])
        return self.object

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        context = self.get_context_data(
            tally_id=self.kwargs["tally_id"], form=form
        )

        return self.render_to_response(context)

    def form_valid(self, form):
        """Handle a valid form submission."""
        try:
            super().form_valid(form)
            messages.success(self.request, _("Tally updated successfully"))
            return self.render_to_response(
                self.get_context_data(
                    form=form, tally_id=self.kwargs["tally_id"]
                )
            )
        except Exception as e:
            messages.error(
                self.request, _("Error updating tally: %(error)s") % {
                    'error': str(e)}
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle an invalid form submission."""
        messages.error(self.request, _("Please correct the errors below."))
        return self.render_to_response(
            self.get_context_data(form=form, tally_id=self.kwargs["tally_id"])
        )


class TallyRemoveView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    TemplateView,
):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "tally_manager/tally_remove.html"

    def get(self, *args, **kwargs):
        tally = Tally.objects.get(id=self.kwargs["tally_id"])

        return self.render_to_response(self.get_context_data(tally=tally))

    def post(self, *args, **kwargs):
        tally = Tally.objects.get(id=self.kwargs["tally_id"])
        tally.active = False
        tally.save()

        return redirect("tally-list")


class TallyFilesFormView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/tally_files_form.html"
    form_class = TallyFilesForm
    success_url = "batch-view"

    def get_initial(self):
        initial = super(TallyFilesFormView, self).get_initial()
        initial["tally_id"] = self.kwargs["tally_id"]

        return initial

    def form_valid(self, form):
        data = form.cleaned_data
        tally_id = data["tally_id"]

        tally = Tally.objects.get(id=tally_id)

        delete_all_tally_objects(tally)

        ballots_file_name_prefix = FILE_NAMES_PREFIXS["ballots_file"]
        ballots_file = f"{ballots_file_name_prefix}{tally_id}.csv"
        ballots_file_lines = save_file(data["ballots_file"], ballots_file)

        subconst_file_name_prefix = FILE_NAMES_PREFIXS["subconst_file"]
        subconst_file = f"{subconst_file_name_prefix}{tally_id}.csv"
        subconst_file_lines = save_file(data["subconst_file"], subconst_file)

        subconst_ballots_file_name_prefix = FILE_NAMES_PREFIXS[
            "subconst_ballots_file"
        ]
        subconst_ballots_file = (
            f"{subconst_ballots_file_name_prefix}{tally_id}.csv"
        )
        subconst_ballots_file_lines = save_file(
            data["subconst_ballots_file"], subconst_ballots_file
        )

        centers_file_name_prefix = FILE_NAMES_PREFIXS["centers_file"]
        centers_file = f"{centers_file_name_prefix}{tally_id}.csv"
        centers_file_lines = save_file(data["centers_file"], centers_file)

        stations_file_name_prefix = FILE_NAMES_PREFIXS["stations_file"]
        stations_file = f"{stations_file_name_prefix}{tally_id}.csv"
        stations_file_lines = save_file(data["stations_file"], stations_file)

        candidates_file_name_prefix = FILE_NAMES_PREFIXS["candidates_file"]
        candidates_file = f"{candidates_file_name_prefix}{tally_id}.csv"
        candidates_file_lines = save_file(
            data["candidates_file"], candidates_file
        )

        ballots_order_file_name_prefix = FILE_NAMES_PREFIXS[
            "ballots_order_file"
        ]
        ballots_order_file = f"{ballots_order_file_name_prefix}{tally_id}.csv"
        ballots_order_file_lines = save_file(
            data["ballots_order_file"], ballots_order_file
        )

        result_forms_file_name_prefix = FILE_NAMES_PREFIXS["result_forms_file"]
        result_forms_file = f"{result_forms_file_name_prefix}{tally_id}.csv"
        result_forms_file_lines = save_file(
            data["result_forms_file"], result_forms_file
        )

        url_kwargs = {
            "tally_id": tally_id,
            "ballots_file": ballots_file,
            "ballots_file_lines": ballots_file_lines,
            "subconst_file": subconst_file,
            "subconst_file_lines": subconst_file_lines,
            "subconst_ballots_file": subconst_ballots_file,
            "subconst_ballots_file_lines": subconst_ballots_file_lines,
            "centers_file": centers_file,
            "centers_file_lines": centers_file_lines,
            "stations_file": stations_file,
            "stations_file_lines": stations_file_lines,
            "candidates_file": candidates_file,
            "candidates_file_lines": candidates_file_lines,
            "ballots_order_file": ballots_order_file,
            "ballots_order_file_lines": ballots_order_file_lines,
            "result_forms_file": result_forms_file,
            "result_forms_file_lines": result_forms_file_lines,
        }

        return HttpResponseRedirect(
            reverse(self.success_url, kwargs=url_kwargs)
        )


class BatchView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    SuccessMessageMixin,
    TemplateView,
):
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/batch_progress.html"

    def get(self, *args, **kwargs):
        context_data = self.kwargs
        tally_id = self.kwargs.get("tally_id")
        context_data["import_progress_url"] = reverse(
            "get-import-progress", kwargs={"tally_id": tally_id}
        )

        return self.render_to_response(self.get_context_data(**context_data))

    @method_decorator(ensure_csrf_cookie)
    def post(self, request, *args, **kwargs):
        tally = Tally.objects.get(id=kwargs["tally_id"])
        current_step = int(request.POST.get("step", 1))

        elements_processed, error_message = process_batch_step(
            current_step, kwargs, tally
        )

        if error_message:
            delete_all_tally_objects(tally)
            return HttpResponse(
                json.dumps(
                    {"status": "Error", "error_message": str(error_message)}
                ),
                content_type="application/json",
            )

        return HttpResponse(
            json.dumps(
                {"status": "OK", "elements_processed": elements_processed}
            ),
            content_type="application/json",
        )


def get_job_status_from_memcache(memcache_key, memcache_client):
    """
    Get incremental count of elements processed from memcache.

    :param memcache_key: memcache key.
    :param memcache_client: memcache client.
    :returns: elements processed, done state and error message.
    """
    error_message = None
    elements_processed = 0
    done = False

    cached_data, error_message = memcache_client.get(memcache_key)
    if cached_data:
        json_data = json.loads(cached_data)
        elements_processed = parse_int(json_data.get("elements_processed"))
        done = json_data.get("done")

    if done:
        _, error_message = memcache_client.delete(memcache_key)

    return elements_processed, done, error_message


def get_import_progress(request, **kwargs):
    """
    Get file import job progress from celery task and if the job is still in
    PENDING status, get incremental count of elements processed from memcache.

    :param request: request dictionary.
    :param kwargs: kwargs.
    :returns: Json response of elements processed or error message.
    """
    tally_id = kwargs.get("tally_id")
    task_id = request.POST.get("task_id")
    current_step = parse_int(request.POST.get("step"))
    instances_count_memcache_key = (
        f"{tally_id}_{STEP_TO_ARGS[current_step][0]}_{current_step}"
    )
    result_form_upload_step = list(STEP_TO_ARGS.keys())[-1]
    result_form_upload_step_timeout_in_seconds = 5
    default_upload_timeout_in_seconds = 1
    error_message = None
    elements_processed = 0
    done = False
    memcache_client = MemCache()
    celery_results = AsyncResult(task_id)
    job_status = celery_results.status
    job_data = celery_results.result

    if job_status == "SUCCESS":
        elements_processed = job_data
        done = True
        _, error_message = memcache_client.delete(instances_count_memcache_key)

    if job_status == "FAILURE":
        error_message = job_data
        done = False
        memcache_client.delete(instances_count_memcache_key)

    if job_status == "PENDING":
        elements_processed, done, error_message = get_job_status_from_memcache(
            instances_count_memcache_key, memcache_client
        )
        if elements_processed == 0:
            if current_step == result_form_upload_step:
                time.sleep(result_form_upload_step_timeout_in_seconds)
        else:
            time.sleep(default_upload_timeout_in_seconds)

    if error_message:
        return HttpResponse(
            json.dumps(
                {"status": "Error", "error_message": str(error_message)}
            ),
            content_type="application/json",
        )

    return HttpResponse(
        json.dumps(
            {
                "status": "OK",
                "elements_processed": elements_processed,
                "done": done,
            }
        ),
        content_type="application/json",
    )


class SetUserTimeOutView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = SiteInfo
    form_class = SiteInfoForm
    group_required = groups.TALLY_MANAGER
    template_name = "tally_manager/set_user_timeout.html"
    success_url = "tally-manager"

    def get_object(self):
        site_id = self.kwargs.get("site_id")

        return get_object_or_404(Site, pk=site_id)

    def get(self, *args, **kwargs):
        user_idle_timeout = None
        self.object = self.get_object()

        try:
            siteinfo = SiteInfo.objects.get(site__pk=self.object.pk)
            user_idle_timeout = siteinfo.user_idle_timeout
        except SiteInfo.DoesNotExist:
            user_idle_timeout = getattr(settings, "DEFAULT_IDLE_TIMEOUT")

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, userIdleTimeout=user_idle_timeout)
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            site_info = form.save()

            if isinstance(site_info, SiteInfo):
                self.success_message = _(
                    "Successfully set user timeout to %(user_idle_timeout)s"
                    " minutes"
                    % {"user_idle_timeout": site_info.user_idle_timeout}
                )

            return redirect(self.success_url)

        user_idle_timeout = None

        try:
            siteinfo = SiteInfo.objects.get(site__pk=self.object.pk)
            user_idle_timeout = siteinfo.user_idle_timeout
        except SiteInfo.DoesNotExist:
            user_idle_timeout = getattr(settings, "DEFAULT_IDLE_TIMEOUT")

        return self.render_to_response(
            self.get_context_data(form=form, userIdleTimeout=user_idle_timeout)
        )
