import dateutil.parser
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import SuspiciousOperation
from django.core.serializers.json import DjangoJSONEncoder, json
from django.db import transaction
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.forms.confirm_reset_form import ConfirmResetForm
from tally_ho.apps.tally.forms.recon_form import ReconForm
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.verify.quarantine_checks import check_quarantine
from tally_ho.libs.views.form_state import form_in_state, safe_form_in_state
from tally_ho.libs.views.mixins import (
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    TallyAccessMixin,
)
from tally_ho.libs.views.session import session_matches_post_result_form


def save_result_form_processing_stats(
    request, encoded_start_time, result_form
):
    """Save result form processing stats.

    :param request: The request object.
    :param encoded_start_time: The encoded time the result form started
        to be processed.
    :param result_form: The result form being processed by the quality control
        clerk.
    """
    qa_control_start_time = dateutil.parser.parse(encoded_start_time)
    del request.session["encoded_result_form_qa_control_start_time"]

    qa_control_end_time = timezone.now()
    form_processing_time_in_seconds = (
        qa_control_end_time - qa_control_start_time
    ).total_seconds()

    ResultFormStats.objects.get_or_create(
        processing_time=form_processing_time_in_seconds,
        user=request.user.userprofile,
        result_form=result_form,
    )


def result_form_results(result_form, active=True, workflow_request_pk=None):
    """Return the results from this form.

    :param result_form: The result form to return results for.
    :param active: Whether to filter results by active.
    :param workflow_request_pk: The workflow request pk to filter results by.

    :returns: A queryset of results for this form.
    """
    election_level = result_form.ballot.electrol_race.election_level
    results = result_form.results.filter(
        active=active,
        entry_version=EntryVersion.FINAL,
        candidate__ballot__electrol_race__election_level=election_level,
    ).order_by("candidate__order")

    if workflow_request_pk:
        results = results.filter(
            deactivated_by_request__pk=workflow_request_pk
        )

    return results


class QualityControlView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = BarcodeForm
    group_required = [
        groups.QUALITY_CONTROL_CLERK,
        groups.QUALITY_CONTROL_SUPERVISOR,
    ]
    template_name = "barcode_verify.html"
    success_url = "quality-control-dashboard"

    def get_context_data(self, **kwargs):
        context = super(QualityControlView, self).get_context_data(**kwargs)
        context["tally_id"] = self.kwargs.get("tally_id")
        context["form_action"] = ""
        context["header_text"] = _("Quality Control & Archiving")
        self.request.session["encoded_result_form_qa_control_start_time"] = (
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))
        )

        return context

    def get_initial(self):
        initial = super(QualityControlView, self).get_initial()
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
            form = safe_form_in_state(
                result_form,
                [FormState.QUALITY_CONTROL, FormState.ARCHIVING],
                form,
            )

            if form:
                return self.form_invalid(form)

            self.request.session["result_form"] = result_form.pk
            QualityControl.objects.create(
                result_form=result_form, user=self.request.user.userprofile
            )

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)


class QualityControlDashboardView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = BarcodeForm
    group_required = [
        groups.QUALITY_CONTROL_CLERK,
        groups.QUALITY_CONTROL_SUPERVISOR,
    ]
    template_name = "quality_control/dashboard.html"
    success_url = "quality-control-print"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        pk = self.request.session.get("result_form")
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, [FormState.QUALITY_CONTROL])

        reconciliation_form = (
            ReconForm(data=model_to_dict(result_form.reconciliationform))
            if result_form.reconciliationform
            else None
        )
        election_level = result_form.ballot.electrol_race.election_level
        results = result_form_results(result_form)

        return self.render_to_response(
            self.get_context_data(
                result_form=result_form,
                reconciliation_form=reconciliation_form,
                results=results,
                header_text=election_level,
                tally_id=tally_id,
            )
        )

    def post(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        quality_control = result_form.qualitycontrol
        url = self.success_url
        ballot = Ballot.objects.get(id=result_form.ballot_id)
        form_ballot_marked_as_released = ballot.available_for_release

        if "correct" in post_data:
            # send to dashboard
            quality_control.passed_qc = True
            quality_control.passed_reconciliation = True
            result_form.save()

            # run quarantine checks
            check_quarantine(result_form, self.request.user)
        elif "incorrect" in post_data:
            # send to confirm reject page
            if form_ballot_marked_as_released:
                url = "quality-control-confirm-reject"
            # send to reject page
            else:
                quality_control.passed_qc = False
                quality_control.passed_reconciliation = False
                quality_control.active = False
                result_form.reject()

                url = "quality-control-reject"

                encoded_start_time = self.request.session.get(
                    "encoded_result_form_qa_control_start_time"
                )
                # Track quality control clerks result form processing time
                # when a form is rejected without confirmation
                save_result_form_processing_stats(
                    self.request, encoded_start_time, result_form
                )

                del self.request.session["result_form"]
        elif "abort" in post_data:
            # send to entry
            quality_control.active = False

            url = "quality-control"
            del self.request.session["result_form"]
        else:
            raise SuspiciousOperation("Missing expected POST data")

        if not form_ballot_marked_as_released:
            quality_control.save()

        return redirect(url, tally_id=tally_id)


class PrintView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = BarcodeForm
    group_required = [
        groups.QUALITY_CONTROL_CLERK,
        groups.QUALITY_CONTROL_SUPERVISOR,
    ]
    template_name = "quality_control/print_cover.html"
    success_url = "quality-control-success"

    def get(self, *args, **kwargs):
        """Display print view with a cover for audit if an audit exists
        for the form, otherwise with a cover for archive.
        """
        pk = self.request.session.get("result_form")
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)

        # Check if cover printing is enabled for quality control
        if not result_form.tally.print_cover_in_quality_control:
            # If printing is disabled, move directly to next state
            result_form.form_state = (
                FormState.AUDIT if result_form.audit else FormState.ARCHIVED
            )
            result_form.save()
            return redirect(self.success_url, tally_id=result_form.tally.id)

        return self.render_to_response(
            self.get_context_data(result_form=result_form)
        )

    @transaction.atomic
    def post(self, *args, **kwargs):
        """We arrive here after the cover has been printed and the user
        confirms this with a button click. Fetch form and if form had an audit,
        set it to audit state, otherwise to archived state.
        """
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.QUALITY_CONTROL)
        tally_id = kwargs.get("tally_id")

        result_form.form_state = (
            FormState.AUDIT if result_form.audit else FormState.ARCHIVED
        )
        result_form.save()

        return redirect(self.success_url, tally_id=tally_id)


class ConfirmationView(
    LoginRequiredMixin, GroupRequiredMixin, TemplateView
):
    template_name = "success.html"
    group_required = [
        groups.QUALITY_CONTROL_CLERK,
        groups.QUALITY_CONTROL_SUPERVISOR,
    ]

    def get(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        pk = self.request.session.get("result_form")
        result_form = get_object_or_404(ResultForm, pk=pk)

        encoded_start_time = self.request.session.get(
            "encoded_result_form_qa_control_start_time"
        )
        # Track quality control clerks result form processing time
        save_result_form_processing_stats(
            self.request, encoded_start_time, result_form
        )

        del self.request.session["result_form"]

        next_step = (
            _("Audit")
            if result_form.form_state == FormState.AUDIT
            else _("Archiving")
        )

        return self.render_to_response(
            self.get_context_data(
                result_form=result_form,
                header_text=_("Quality Control"),
                next_step=next_step,
                tally_id=tally_id,
                start_url="quality-control",
                clearance_error=None,
            )
        )


class ConfirmFormResetView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    SuccessMessageMixin,
    FormView,
):
    form_class = ConfirmResetForm
    group_required = [
        groups.QUALITY_CONTROL_CLERK,
        groups.QUALITY_CONTROL_SUPERVISOR,
    ]
    template_name = "quality_control/confirm_form_reset.html"
    success_url = "quality-control-reject"

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        tally_id = kwargs.get("tally_id")

        if form.is_valid():
            reject_reason = form.data.get("reject_reason")
            result_form_pk = self.request.session.get("result_form")
            result_form = ResultForm.objects.get(id=result_form_pk)
            quality_control = result_form.qualitycontrol
            quality_control.passed_qc = False
            quality_control.passed_reconciliation = False
            quality_control.active = False
            result_form.reject(reject_reason=reject_reason)
            quality_control.save()

            encoded_start_time = self.request.session.get(
                "encoded_result_form_qa_control_start_time"
            )
            # Track quality control clerks result form processing time
            # when rejecting a form
            save_result_form_processing_stats(
                self.request, encoded_start_time, result_form
            )

            del self.request.session["result_form"]

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)
