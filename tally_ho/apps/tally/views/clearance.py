import dateutil.parser
from django.core.serializers.json import DjangoJSONEncoder, json
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.forms.clearance_form import ClearanceForm
from tally_ho.apps.tally.models.clearance import Clearance
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.models.enums.clearance_resolution import ClearanceResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.time import now
from tally_ho.libs.views.form_state import form_in_state, safe_form_in_state
from tally_ho.libs.views.mixins import (GroupRequiredMixin,
                                        PrintedResultFormMixin,
                                        ReverseSuccessURLMixin,
                                        TallyAccessMixin)
from tally_ho.libs.views.pagination import paging
from tally_ho.libs.views.session import session_matches_post_result_form


def clearance_action(post_data, clearance, result_form, url):
    if "forward" in post_data:
        # forward to supervisor
        clearance.reviewed_team = True
        url = "clearance-print"

    if "return" in post_data:
        # return to audit team
        clearance.reviewed_team = False
        clearance.reviewed_supervisor = False

    if "implement" in post_data:
        # take implementation action
        clearance.reviewed_supervisor = True

        if (
            clearance.resolution_recommendation
            == ClearanceResolution.PENDING_FIELD_INPUT
        ):
            clearance.active = True
            clearance.reviewed_supervisor = False

        if (
            clearance.resolution_recommendation
            == ClearanceResolution.RESET_TO_PREINTAKE
        ):
            clearance.active = False
            result_form.form_state = FormState.UNSUBMITTED
            result_form.duplicate_reviewed = False
            if result_form.is_replacement:
                result_form.center = None
                result_form.station_number = None
            result_form.save()

    clearance.save()

    return url


def get_clearance(result_form, post_data, user, form):
    """Fetch the clearance or build it form the result form and form.

    :param result_form: The form get or create a clearance for.
    :param post_data: The post data to create a clearance form from.
    :param user: The user to assign this clearance to.
    :param form: The form to create a new clearance from.
    """
    clearance = result_form.clearance
    userprofile = user.userprofile

    if clearance:
        clearance = ClearanceForm(post_data, instance=clearance).save(
            commit=False
        )

        if groups.CLEARANCE_CLERK in user.groups.values_list(
            "name", flat=True
        ):
            clearance.user = userprofile
        else:
            clearance.supervisor = userprofile
    else:
        clearance = form.save(commit=False)
        clearance.result_form = result_form
        clearance.user = userprofile

    if groups.CLEARANCE_CLERK in user.groups.values_list("name", flat=True):
        clearance.date_team_modified = now()
    else:
        clearance.date_supervisor_modified = now()

    return clearance


def is_clerk(user):
    return groups.CLEARANCE_CLERK in user.groups.values_list("name", flat=True)


def save_result_form_processing_stats(
    request, encoded_start_time, result_form
):
    """Save result form processing stats.

    :param request: The request object.
    :param encoded_start_time: The encoded time the result form started
        to be processed.
    :param result_form: The result form being processed by the clearance
        clerk.
    """
    clearance_start_time = dateutil.parser.parse(encoded_start_time)
    del request.session["encoded_result_form_clearance_start_time"]

    clearance_end_time = timezone.now()
    form_processing_time_in_seconds = (
        clearance_end_time - clearance_start_time
    ).total_seconds()

    ResultFormStats.objects.get_or_create(
        processing_time=form_processing_time_in_seconds,
        user=request.user.userprofile,
        result_form=result_form,
    )


class DashboardView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = ClearanceForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/dashboard.html"
    success_url = "clearance-review"

    def get(self, *args, **kwargs):
        format_ = kwargs.get("format")
        tally_id = kwargs.get("tally_id")
        form_list = ResultForm.objects.filter(
            form_state=FormState.CLEARANCE, tally__id=tally_id
        )

        if format_ == "csv":
            return render_to_csv_response(form_list)

        forms = paging(form_list, self.request)

        return self.render_to_response(
            self.get_context_data(
                forms=forms,
                is_clerk=is_clerk(self.request.user),
                tally_id=tally_id,
            )
        )

    def post(self, *args, **kwargs):
        self.request.session["encoded_result_form_clearance_start_time"] = (
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))
        )
        tally_id = kwargs.get("tally_id")
        post_data = self.request.POST
        pk = post_data["result_form"]
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.CLEARANCE)
        self.request.session["result_form"] = result_form.pk

        return redirect(self.success_url, tally_id=tally_id)


class ReviewView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = ClearanceForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/review.html"
    success_url = "clearance"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        pk = self.request.session["result_form"]
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_class = self.get_form_class()
        clearance = result_form.clearance
        form = (
            ClearanceForm(instance=clearance)
            if clearance
            else self.get_form(form_class)
        )

        return self.render_to_response(
            self.get_context_data(
                form=form,
                result_form=result_form,
                is_clerk=is_clerk(self.request.user),
                tally_id=tally_id,
            )
        )

    def post(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        user = self.request.user
        form_class = self.get_form_class()
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.CLEARANCE)
        form = self.get_form(form_class)

        encoded_start_time = self.request.session.get(
            "encoded_result_form_clearance_start_time"
        )
        # Track clearance clerks review result form processing time
        save_result_form_processing_stats(
            self.request, encoded_start_time, result_form
        )

        if form.is_valid():
            clearance = get_clearance(result_form, post_data, user, form)
            url = clearance_action(
                post_data, clearance, result_form, self.success_url
            )

            return redirect(url, tally_id=tally_id)
        else:
            return self.render_to_response(
                self.get_context_data(
                    form=form, result_form=result_form, tally_id=tally_id
                )
            )


class PrintCoverView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    TemplateView,
):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "clearance/print_cover.html"
    printed_url = "clearance-printed"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        pk = self.request.session.get("result_form")
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.CLEARANCE)
        problems = result_form.clearance.get_problems()

        # Check if cover printing is enabled for clearance
        if not result_form.tally.print_cover_in_clearance:
            # If printing is disabled, mark as printed and move to next state
            del self.request.session["result_form"]
            return redirect("clearance", tally_id=tally_id)

        return self.render_to_response(
            self.get_context_data(
                result_form=result_form,
                username=self.request.user.username,
                problems=problems,
                printed_url=reverse(self.printed_url, args=(pk,)),
                tally_id=tally_id,
            )
        )

    def post(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        post_data = self.request.POST

        if "result_form" in post_data:
            pk = session_matches_post_result_form(post_data, self.request)

            result_form = get_object_or_404(
                ResultForm, pk=pk, tally__id=tally_id
            )
            form_in_state(result_form, FormState.CLEARANCE)
            del self.request.session["result_form"]

            return redirect("clearance", tally_id=tally_id)

        return self.render_to_response(
            self.get_context_data(result_form=result_form, tally_id=tally_id)
        )


class CreateClearanceView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    FormView,
):
    form_class = BarcodeForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    success_url = "clearance-check-center-details"
    template_name = "barcode_verify.html"

    def get_context_data(self, **kwargs):
        self.request.session["encoded_result_form_clearance_start_time"] = (
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))
        )
        tally_id = self.kwargs.get("tally_id")
        context = super(CreateClearanceView, self).get_context_data(**kwargs)
        context["tally_id"] = tally_id
        context["header_text"] = _("Create Clearance")

        return context

    def get_initial(self):
        initial = super(CreateClearanceView, self).get_initial()
        initial["tally_id"] = self.kwargs.get("tally_id")

        return initial

    def post(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = (
                form.cleaned_data["barcode"]
                or form.cleaned_data["barcode_scan"]
            )
            result_form = get_object_or_404(
                ResultForm, barcode=barcode, tally__id=tally_id
            )

            possible_states = [
                FormState.CORRECTION,
                FormState.DATA_ENTRY_1,
                FormState.DATA_ENTRY_2,
                FormState.INTAKE,
                FormState.QUALITY_CONTROL,
                FormState.ARCHIVING,
                FormState.UNSUBMITTED,
            ]

            if groups.SUPER_ADMINISTRATOR in groups.user_groups(
                self.request.user
            ):
                possible_states.append(FormState.ARCHIVED)

            form = safe_form_in_state(result_form, possible_states, form)

            if form:
                return self.form_invalid(form)

            self.request.session["result_form"] = result_form.pk

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)


class CheckCenterDetailsView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = BarcodeForm
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    template_name = "check_clearance_center_details.html"
    success_url = "clearance-add"

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get("tally_id")
        pk = self.request.session.get("result_form")

        context = super(CheckCenterDetailsView, self).get_context_data(
            **kwargs
        )
        context["tally_id"] = tally_id
        context["header_text"] = _("Clearance")
        context["form_action"] = reverse(
            self.success_url, kwargs={"tally_id": tally_id}
        )
        # There may be instances where the result form is not known for example
        # if the wrong barcode was entered and there is no result form with
        # matching barcode and as such the pk is not set.
        if pk:
            context["result_form"] = get_object_or_404(
                ResultForm, pk=pk, tally__id=tally_id
            )

        return context

    def get_initial(self):
        initial = super(CheckCenterDetailsView, self).get_initial()
        initial["tally_id"] = self.kwargs.get("tally_id")

        return initial


class AddClearanceFormView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    FormView,
):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]
    success_url = "clearance"

    def post(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        post_data = self.request.POST
        pk = self.request.POST.get("result_form", None)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        accept_submit_text_in_post_data = "accept_submit" in post_data

        if accept_submit_text_in_post_data:
            result_form.reject(FormState.CLEARANCE)
            Clearance.objects.create(
                result_form=result_form, user=self.request.user.userprofile
            )

        result_form.date_seen = now()
        result_form.save()

        # Track clearance clerks new clearance case result form processing time
        if accept_submit_text_in_post_data:
            encoded_start_time = self.request.session.get(
                "encoded_result_form_clearance_start_time"
            )
            save_result_form_processing_stats(
                self.request, encoded_start_time, result_form
            )

        return redirect(self.success_url, tally_id=tally_id)


class ClearancePrintedView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    PrintedResultFormMixin,
    TemplateView,
):
    group_required = [groups.CLEARANCE_CLERK, groups.CLEARANCE_SUPERVISOR]

    def set_printed(self, result_form):
        result_form.clearance_printed = True
        result_form.save()
