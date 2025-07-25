import dateutil.parser
from django.core.exceptions import SuspiciousOperation
from django.core.serializers.json import DjangoJSONEncoder, json
from django.db import transaction
from django.forms.formsets import formset_factory
from django.forms.utils import ErrorList
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.barcode_form import BarcodeForm
from tally_ho.apps.tally.forms.candidate_form import CandidateForm
from tally_ho.apps.tally.forms.candidate_formset import BaseCandidateFormSet
from tally_ho.apps.tally.forms.center_details_form import CenterDetailsForm
from tally_ho.apps.tally.forms.create_result_form import CreateResultForm
from tally_ho.apps.tally.forms.recon_form import ReconForm
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.errors import add_generic_error
from tally_ho.libs.views.form_state import (form_in_data_entry_state,
                                            safe_form_in_state)
from tally_ho.libs.views.mixins import (GroupRequiredMixin,
                                        ReverseSuccessURLMixin,
                                        TallyAccessMixin)
from tally_ho.libs.views.session import session_matches_post_result_form


def get_data_entry_number(form_state):
    """Return data entry number from form state."""
    return 1 if form_state in [FormState.DATA_ENTRY_1] else 2


def get_formset_and_candidates(result_form, post_data=None):
    """Return a formset with the candidates and race types for this result
    form.

    :param result_form: The result form to get candidates for.
    :param post_date: The post data to initialize the form with.

    :returns: A form set and list of candidates race type, form, and candidate
        tuples.
    """
    candidates = result_form.candidates

    CandidateFormSet = formset_factory(
        CandidateForm, extra=len(candidates), formset=BaseCandidateFormSet
    )
    formset = CandidateFormSet(post_data) if post_data else CandidateFormSet()
    forms_and_candidates = []
    last_election_level = None
    last_sub_race_type = None
    tabindex = 200

    for i, f in enumerate(formset):
        candidate = candidates[i]
        election_level = (
            candidate.ballot.electrol_race.election_level
            if candidate.ballot.electrol_race.election_level
            != last_election_level
            else None
        )
        sub_race_type = (
            candidate.ballot.electrol_race.ballot_name
            if candidate.ballot.electrol_race.ballot_name != last_sub_race_type
            else None
        )
        last_election_level = candidate.ballot.electrol_race.election_level
        last_sub_race_type = candidate.ballot.electrol_race.ballot_name
        f.fields["votes"].widget.attrs["tabindex"] = tabindex
        tabindex += 10
        forms_and_candidates.append(
            [election_level, sub_race_type, f, candidate]
        )

    return [formset, forms_and_candidates]


def get_header_text(result_form):
    data_entry_number = get_data_entry_number(result_form.form_state)
    return _("Data Entry") + " %s" % data_entry_number


def user_is_data_entry_1(user):
    return groups.DATA_ENTRY_1_CLERK in groups.user_groups(user)


def user_is_data_entry_2(user):
    return groups.DATA_ENTRY_2_CLERK in groups.user_groups(user)


def check_group_for_state(result_form, user, form):
    """Ensure only data entry 1 clerk can access forms in data entry 1 state
    and similarly for data entry 2.

    Always allow access for the super administrator.

    :param result_form: The result form to check access to.
    :param user: The user to check group of.
    :param form: The Django form to attach an error to.

    :returns: A form with an error if access denied, else None.
    """
    if set([groups.SUPER_ADMINISTRATOR, groups.TALLY_MANAGER]).intersection(
        set(groups.user_groups(user))
    ):
        return None

    if (
        result_form.form_state == FormState.DATA_ENTRY_1
        and not user_is_data_entry_1(user)
    ) or (
        result_form.form_state == FormState.DATA_ENTRY_2
        and not user_is_data_entry_2(user)
    ):
        message = _("Return form to %(state)s") % {
            'state': result_form.form_state_name
        }

        return add_generic_error(form, message)


def check_form_for_center_station(center, station_number, result_form):
    """Validate that the center and station are assigned to this result form.

    :param center: The center to check.
    :param station_number: The station number to check.
    :param result_form: The result form to check the center and station number
        for.

    :raises: `SuspiciousOperation` if the result_form is not for this center
        and station.
    """
    if result_form not in ResultForm.objects.filter(
        center=center, station_number=station_number
    ):
        raise SuspiciousOperation(_("Center and station numbers do not match"))


def check_state_and_group(result_form, user, form):
    """Check that the result_form is in the correct state for the user.

    :param result_form: The result form to check the state of.
    :param user: The user to check the state for.
    :param form: A form to add errors to if any exist.

    :returns: A form with an error the form and user do not match, otherwise
        None.
    """
    check_state = safe_form_in_state(
        result_form, [FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_2], form
    )
    check_group = check_group_for_state(result_form, user, form)

    return check_state or check_group


class DataEntryView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = BarcodeForm
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]
    template_name = "barcode_verify.html"
    success_url = "data-entry-enter-center-details"

    def get_context_data(self, **kwargs):
        context = super(DataEntryView, self).get_context_data(**kwargs)

        user = self.request.user

        is_admin = entry_type = None

        if user_is_data_entry_1(user):
            entry_type = 1
        elif user_is_data_entry_2(user):
            entry_type = 2
        else:
            is_admin = True

        context["tally_id"] = self.kwargs.get("tally_id")
        context["form_action"] = ""
        context["header_text"] = _("Data Entry %(entry_type)s") % {
                'entry_type': entry_type if not is_admin else _("Admin")}

        if entry_type is not is_admin:
            self.request.session[
                "encoded_result_form_data_entry_start_time"
            ] = json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))

        return context

    def get_initial(self):
        initial = super(DataEntryView, self).get_initial()
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
            check_form = check_state_and_group(
                result_form, self.request.user, form
            )

            if check_form:
                return self.form_invalid(check_form)

            self.request.session["result_form"] = result_form.pk

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)


class CenterDetailsView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = CenterDetailsForm
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]
    template_name = "enter_center_details.html"
    success_url = "enter-results"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self, "_result_form") and "result_form" not in kwargs:
            context["result_form"] = getattr(self, "_result_form")
            context["header_text"] = get_header_text(context["result_form"])

        return context

    def get(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        self.initial = {
            "tally_id": tally_id,
        }
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        pk = self.request.session.get("result_form")
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_data_entry_state(result_form)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                result_form=result_form,
                header_text=get_header_text(result_form),
                tally_id=tally_id,
            )
        )

    def post(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = self._result_form = get_object_or_404(
            ResultForm, pk=pk, tally__id=tally_id
        )

        if form.is_valid():
            check_form = check_state_and_group(
                result_form, self.request.user, form
            )

            if check_form:
                return self.form_invalid(check_form)

            center_number = form.cleaned_data["center_number"]
            center = Center.objects.get(code=center_number, tally__id=tally_id)
            station_number = form.cleaned_data["station_number"]

            try:
                check_form_for_center_station(
                    center, station_number, result_form
                )
            except SuspiciousOperation as e:
                errors = form._errors.setdefault("__all__", ErrorList())
                errors.append(e)
            else:
                check_form = check_state_and_group(
                    result_form, self.request.user, form
                )

                if check_form:
                    return self.form_invalid(check_form)

                return redirect(self.success_url, tally_id=tally_id)
        return self.render_to_response(
            self.get_context_data(
                form=form,
                result_form=result_form,
                tally_id=tally_id,
                header_text=get_header_text(result_form),
            )
        )


class EnterResultsView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    ReverseSuccessURLMixin,
    FormView,
):
    form_class = CreateResultForm
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]
    template_name = "data_entry/enter_results_view.html"
    success_url = "data-entry-success"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        pk = self.request.session.get("result_form")
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_data_entry_state(result_form)
        formset, forms_and_candidates = get_formset_and_candidates(result_form)
        reconciliation_form = ReconForm()
        data_entry_number = get_data_entry_number(result_form.form_state)

        return self.render_to_response(
            self.get_context_data(
                formset=formset,
                forms_and_candidates=forms_and_candidates,
                reconciliation_form=reconciliation_form,
                result_form=result_form,
                data_entry_number=data_entry_number,
                tally_id=tally_id,
            )
        )

    @transaction.atomic
    def post(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_data_entry_state(result_form)
        formset, forms_and_candidates = get_formset_and_candidates(
            result_form, post_data
        )
        recon_form = ReconForm(post_data)
        data_entry_number = get_data_entry_number(result_form.form_state)
        candidates = result_form.candidates
        CandidateFormSet = formset_factory(
            CandidateForm, extra=len(candidates), formset=BaseCandidateFormSet
        )
        formset = CandidateFormSet(post_data)

        if result_form.form_state == FormState.DATA_ENTRY_1:
            all_zero = True
            has_votes = False

            for i, form in enumerate(formset.forms):
                form.is_valid()
                votes = form.cleaned_data.get("votes")
                if votes:
                    has_votes = True
                    if int(votes) > 0:
                        all_zero = False
                        break
            has_vote_data_error = not has_votes or all_zero
            has_invalid_recon_form = (
                result_form.has_recon and not recon_form.is_valid()
            )

            if has_vote_data_error or has_invalid_recon_form:
                error_message = _(
                    str(
                        "Form rejected: All candidate votes "
                        "are blank or zero, or reconciliation form "
                        "is invalid."
                    )
                )

                result_form.reject(
                    new_state=FormState.CLEARANCE, reject_reason=error_message
                )
                self.request.session["clearance_error"] = str(error_message)
                return redirect(self.success_url, tally_id=tally_id)

        if (
            not result_form.has_recon or recon_form.is_valid()
        ) and formset.is_valid():
            check_form = check_state_and_group(
                result_form, self.request.user, recon_form
            )

            if check_form:
                return self.form_invalid(check_form)

            entry_version = None
            new_state = None

            if result_form.form_state == FormState.DATA_ENTRY_1:
                entry_version = EntryVersion.DATA_ENTRY_1
                new_state = FormState.DATA_ENTRY_2
            else:
                entry_version = EntryVersion.DATA_ENTRY_2
                new_state = FormState.CORRECTION

            for i, form in enumerate(formset.forms):
                votes = form.cleaned_data["votes"]
                Result.objects.create(
                    candidate=candidates[i],
                    result_form=result_form,
                    entry_version=entry_version,
                    votes=votes,
                    user=self.request.user.userprofile,
                )

            if result_form.has_recon:
                re_form = recon_form.save(commit=False)
                re_form.entry_version = entry_version
                re_form.result_form = result_form
                re_form.user = self.request.user.userprofile
                re_form.save()

            result_form.form_state = new_state
            result_form.duplicate_reviewed = False
            result_form.save()

            return redirect(self.success_url, tally_id=tally_id)
        return self.render_to_response(
            self.get_context_data(
                formset=formset,
                forms_and_candidates=forms_and_candidates,
                reconciliation_form=recon_form,
                result_form=result_form,
                data_entry_number=data_entry_number,
                tally_id=tally_id,
            )
        )


class ConfirmationView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    TemplateView,
):
    template_name = "success.html"
    group_required = [groups.DATA_ENTRY_1_CLERK, groups.DATA_ENTRY_2_CLERK]

    def get(self, *args, **kwargs):
        tally_id = kwargs.get("tally_id")
        pk = self.request.session.get("result_form")
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        del self.request.session["result_form"]

        user = self.request.user
        if user_is_data_entry_1(user) or user_is_data_entry_2(user):
            data_entry_start_time = dateutil.parser.parse(
                self.request.session.get(
                    "encoded_result_form_data_entry_start_time"
                )
            )
            del self.request.session[
                "encoded_result_form_data_entry_start_time"
            ]

            data_entry_end_time = timezone.now()
            form_processing_time_in_seconds = (
                data_entry_end_time - data_entry_start_time
            ).total_seconds()

            # Track data entry clerks result form processing time
            ResultFormStats.objects.get_or_create(
                processing_time=form_processing_time_in_seconds,
                user=user.userprofile,
                result_form=result_form,
            )

        next_step = (
            _("Data Entry 2")
            if result_form.form_state == FormState.DATA_ENTRY_2
            else _("Corrections")
        )
        clearance_error = None
        if self.request.session.get("clearance_error"):
            clearance_error = self.request.session.pop("clearance_error")
            next_step = _("Clearance")

        return self.render_to_response(
            self.get_context_data(
                result_form=result_form,
                header_text=_("Data Entry"),
                next_step=next_step,
                start_url="data-entry",
                tally_id=tally_id,
                clearance_error=clearance_error,
            )
        )
