"""
Result Form Search and History Views

This module contains views and helper functions for searching result forms
and displaying their version history.
"""

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView
from guardian.mixins import LoginRequiredMixin
from reversion.models import Version

from tally_ho.apps.tally.forms.barcode_form import ResultFormSearchBarcodeForm
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.time import format_duration_human_readable
from tally_ho.libs.views.mixins import GroupRequiredMixin, TallyAccessMixin


def extract_timestamp_from_version(version):
    """Extract and parse timestamp from version.field_dict.

    :param version: The Version instance
    :returns: Parsed datetime object or None
    """
    if not version:
        return None

    version_data = version.field_dict
    modified_date = version_data.get("modified_date")
    if modified_date:
        if isinstance(modified_date, str):
            return parse_datetime(modified_date)
        else:
            return modified_date
    return None


def create_result_form_history_entry(result_form, last_version_timestamp=None):
    """Create history entry from current ResultForm state.

    :param result_form: The ResultForm instance
    :param last_version_timestamp: Timestamp from last version for duration
    :returns: Dictionary with current state history data
    """
    # Get user info
    current_user_name = "Unknown"
    if result_form.user:
        current_user_name = result_form.user.username

    # Get current state info
    current_state_name = FormState(result_form.form_state).name
    previous_state_name = "None"
    if result_form.previous_form_state:
        previous_state_name = FormState(result_form.previous_form_state).name

    # Calculate duration from last version if available
    duration = None
    duration_display = None
    if last_version_timestamp and result_form.modified_date:
        duration = result_form.modified_date - last_version_timestamp
        duration_display = format_duration_human_readable(duration)

    return {
        "user": current_user_name,
        "timestamp": result_form.modified_date,
        "current_state": current_state_name,
        "previous_state": previous_state_name,
        "version_id": None,
        "duration_in_previous_state": duration,
        "duration_display": duration_display,
        "is_current": True,
    }


def create_version_history_entry(version, previous_timestamp=None):
    """Create history entry from a Version object.

    :param version: The Version instance
    :param previous_timestamp: Previous version timestamp for duration calc
    :returns: Dictionary with version history data
    """
    version_data = version.field_dict

    # Get user info
    user_name = "Unknown"
    if "user_id" in version_data and version_data["user_id"]:
        try:
            user = User.objects.get(pk=version_data["user_id"])
            user_name = user.username
        except User.DoesNotExist:
            user_name = f"User ID {version_data['user_id']}"

    # Parse timestamp
    timestamp = extract_timestamp_from_version(version)

    # Get form states
    current_state = version_data.get("form_state")
    previous_state = version_data.get("previous_form_state")

    if current_state:
        current_state_name = FormState(current_state).name
    else:
        current_state_name = "Unknown"

    if previous_state:
        previous_state_name = FormState(previous_state).name
    else:
        previous_state_name = "None"

    # Calculate duration in previous state
    duration = None
    duration_display = None
    if previous_timestamp and timestamp:
        duration = timestamp - previous_timestamp
        duration_display = format_duration_human_readable(duration)

    return {
        "user": user_name,
        "timestamp": timestamp,
        "current_state": current_state_name,
        "previous_state": previous_state_name,
        "version_id": version.pk,
        "duration_in_previous_state": duration,
        "duration_display": duration_display,
        "is_current": False,
    }


def get_result_form_history_data(result_form, versions):
    """Generate complete history data including current state and versions.

    :param result_form: The ResultForm instance
    :param versions: QuerySet of Version objects
    :returns: List of history data dictionaries
    """
    # Get last version timestamp for current entry duration
    last_timestamp = (
        extract_timestamp_from_version(versions.last()) if versions else None
    )

    # Create current state entry
    current_entry = create_result_form_history_entry(
        result_form, last_timestamp
    )

    # Process version history
    history_data = []
    previous_timestamp = None

    for version in versions:
        entry = create_version_history_entry(version, previous_timestamp)
        history_data.append(entry)
        previous_timestamp = entry["timestamp"]

    # Reverse to show newest first, then add current entry at top
    history_data.reverse()
    history_data.insert(0, current_entry)
    return history_data


class ResultFormSearchView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    FormView,
):
    form_class = ResultFormSearchBarcodeForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/result_form_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tally_id"] = self.kwargs.get("tally_id")
        context["header_text"] = _("Result Form History")
        context["form_action"] = ""
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial["tally_id"] = self.kwargs.get("tally_id")
        return initial

    def form_valid(self, form):
        barcode = form.cleaned_data["barcode"]
        tally_id = self.kwargs.get("tally_id")

        try:
            result_form = ResultForm.objects.get(
                barcode=barcode, tally__id=tally_id
            )
        except ResultForm.DoesNotExist:
            form.add_error(
                "barcode",
                _(
                    "Result form with this barcode does not exist "
                    "in this tally."
                ),
            )
            return self.form_invalid(form)

        # Store result form pk in session
        self.request.session["result_form"] = result_form.pk

        return redirect("result-form-history", tally_id=tally_id)


class ResultFormHistoryView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    TemplateView,
):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/result_form_history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tally_id = self.kwargs.get("tally_id")
        pk = self.request.session.get("result_form")

        context["tally_id"] = tally_id
        context["error"] = None  # Initialize error to prevent template errors

        if not pk:
            context["error"] = "No result form selected"
            return context

        try:
            result_form = get_object_or_404(
                ResultForm, pk=pk, tally__id=tally_id
            )
        except Exception:
            context["error"] = "Result form not found"
            return context

        # Get version history
        versions = Version.objects.get_for_object(result_form).order_by("pk")

        # Generate complete history data using helper functions
        history_data = get_result_form_history_data(result_form, versions)

        context.update(
            {
                "result_form": result_form,
                "history_data": history_data,
            }
        )

        return context
