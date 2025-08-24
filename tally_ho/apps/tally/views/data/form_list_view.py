import json

from django.db.models import F, IntegerField, OuterRef, Q, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView
from djqscsv import render_to_csv_response
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.views.constants import (
    at_state_query_param,
    election_level_query_param,
    pending_at_state_query_param,
    show_inactive_query_param,
    sub_con_code_query_param,
    sub_race_query_param,
)
from tally_ho.libs.models.enums.form_state import (
    FormState,
    un_processed_states_at_state,
)
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.enum import get_matching_enum_values
from tally_ho.libs.views.mixins import (
    DataTablesMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
)

ALL = "__all__"


class FormListDataView(
    LoginRequiredMixin, GroupRequiredMixin, TallyAccessMixin, BaseDatatableView
):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    columns = (
        "barcode",
        "center.code",
        "station_id",
        "station_number",
        "office.name",
        "office.number",
        "ballot.number",
        "center.sub_constituency.name",
        "center.sub_constituency.code",
        "ballot.electrol_race.election_level",
        "ballot.electrol_race.ballot_name",
        "center.office.region.name",
        "form_state",
        "modified_date",
        "action",
    )

    def get_order_columns(self):
        """
        Return list of columns that can be ordered.
        Replace 'action' column with empty string since it's virtual and cannot
        be sorted.
        """
        # Keep the same list structure but replace 'action' with empty string
        # This maintains index positions for DataTables
        return [col if col != "action" else "" for col in self.columns]

    def render_column(self, row, column):
        if column == "modified_date":
            return row.modified_date.strftime("%a, %d %b %Y %H:%M:%S %Z")

        if column == "action":
            return row.get_action_button

        return super(FormListDataView, self).render_column(row, column)

    def filter_queryset(self, qs):
        show_inactive = self.request.GET.get(show_inactive_query_param)
        if not show_inactive or show_inactive.lower() != "true":
            qs = qs.filter(ballot__active=True)

        ballot_number = self.request.POST.get("ballot[value]", None)
        tally_id = self.kwargs.get("tally_id")
        keyword = self.request.POST.get("search[value]")

        requested_form_state = self.request.GET.get(at_state_query_param)
        pending_in_form_state = self.request.GET.get(
            pending_at_state_query_param
        )
        election_level = self.request.GET.get(election_level_query_param)
        requested_sub_race = self.request.GET.get(sub_race_query_param)
        requested_sub_con_code = self.request.GET.get(sub_con_code_query_param)

        if requested_form_state:
            state_enum_key = requested_form_state.upper()
            if state_enum_key in FormState.__members__:
                requested_state = FormState[state_enum_key]
                qs = qs.filter(form_state=requested_state)

        if election_level and requested_sub_race:
            filters = {
                "ballot__electrol_race__election_level": election_level,
                "ballot__electrol_race__ballot_name": requested_sub_race,
            }
            if not show_inactive or show_inactive.lower() != "true":
                filters["ballot__active"] = True
            qs = qs.filter(**filters)

        if requested_sub_con_code:
            qs = qs.filter(
                center__sub_constituency__code=requested_sub_con_code
            )

        if pending_in_form_state:
            state_enum_key = pending_in_form_state.upper()
            if state_enum_key in FormState.__members__:
                specified_form_state = FormState[state_enum_key]
                unprocessed_form_state = un_processed_states_at_state(
                    specified_form_state
                )
                if unprocessed_form_state:
                    qs = qs.filter(form_state__in=unprocessed_form_state)

        station_id_query = Subquery(
            Station.objects.filter(
                tally__id=tally_id,
                center__code=OuterRef("center__code"),
                station_number=OuterRef("station_number"),
            ).values("id")[:1],
            output_field=IntegerField(),
        )

        if tally_id:
            qs = qs.filter(tally__id=tally_id).annotate(
                station_id=station_id_query,
            )

        if ballot_number:
            ballot_filters = {"number": ballot_number, "tally__id": tally_id}
            if not show_inactive or show_inactive.lower() != "true":
                ballot_filters["active"] = True
            ballot = get_object_or_404(Ballot, **ballot_filters)
            qs = qs.filter(ballot__number__in=ballot.form_ballot_numbers)

        if keyword:
            # Get matching FormState enum values for case-insensitive search
            matching_states = get_matching_enum_values(FormState, keyword)
            form_state_q = (
                Q(form_state__in=matching_states) if matching_states else Q()
            )

            qs = qs.filter(
                form_state_q
                | Q(barcode__icontains=keyword)
                | Q(center__code__contains=keyword)
                | Q(station_id__contains=keyword)
                | Q(center__office__region__name__icontains=keyword)
                | Q(center__sub_constituency__name__icontains=keyword)
                | Q(center__office__name__icontains=keyword)
                | Q(center__office__number__contains=keyword)
                | Q(station_number__contains=keyword)
                | Q(ballot__number__contains=keyword)
                | Q(ballot__electrol_race__election_level__icontains=keyword)
                | Q(ballot__electrol_race__ballot_name__icontains=keyword)
            )

        return qs


class FormListView(
    LoginRequiredMixin,
    GroupRequiredMixin,
    TallyAccessMixin,
    DataTablesMixin,
    TemplateView,
):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "data/forms.html"

    def get(self, *args, **kwargs):
        form_state = kwargs.get("state")
        tally_id = kwargs.get("tally_id")

        error = self.request.session.get("error_message")
        download_url = "/ajax/download-result-forms/"

        if error:
            del self.request.session["error_message"]

        show_inactive = self.request.GET.get(
            show_inactive_query_param, "false"
        )
        if form_state:
            if form_state == ALL:
                form_list = ResultForm.objects.filter(tally__id=tally_id)
                if not show_inactive or show_inactive.lower() != "true":
                    form_list = form_list.filter(ballot__active=True)
            else:
                form_state = FormState[form_state.upper()]
                form_list = ResultForm.forms_in_state(
                    form_state.value, tally_id=tally_id
                )
                if not show_inactive or show_inactive.lower() != "true":
                    form_list = form_list.filter(ballot__active=True)
            form_list = form_list.values(
                "barcode",
                "ballot__electrol_race__election_level",
                "ballot__electrol_race__ballot_name",
                "ballot__number",
                "center__office__region__name",
                "center__code",
                "office__name",
                "office__number",
                "station_number",
                "center__sub_constituency__name",
                "center__sub_constituency__code",
                "form_state",
            ).order_by("barcode")

            header_map = {
                "barcode": "barcode",
                "center__code": "center code",
                "station_number": "station number",
                "office__name": "office name",
                "office__number": "office number",
                "center__sub_constituency__name": "subconstituency name",
                "center__sub_constituency__code": "subconstituency code",
                "ballot__electrol_race__election_level": "election level",
                "ballot__electrol_race__ballot_name": "sub race type",
                "ballot__number": "ballot number",
                "center__office__region__name": "region name",
                "form_state": "form state",
            }
            report_name = "{}_form_list".format(
                form_state if form_state == ALL else form_state.name
            )

            return render_to_csv_response(
                form_list,
                filename=report_name,
                append_datestamp=True,
                field_header_map=header_map,
            )

        query_param_string = self.request.GET.urlencode()
        remote_data_url = reverse(
            "form-list-data", kwargs={"tally_id": tally_id}
        )
        if query_param_string:
            remote_data_url = f"{remote_data_url}?{query_param_string}"

        additional_context = {"export_file_name": "form-list"}
        return self.render_to_response(
            self.get_context_data(
                header_text=_("Form List"),
                remote_url=remote_data_url,
                tally_id=tally_id,
                error_message=_(error) if error else None,
                show_create_form_button=True,
                result_forms_download_url=download_url,
                show_inactive=show_inactive,
                **additional_context,
            )
        )


class FormNotReceivedListView(FormListView):
    group_required = groups.SUPER_ADMINISTRATOR
    enable_scroll_x = True

    def get(self, *args, **kwargs):
        format_ = kwargs.get("format")
        tally_id = kwargs.get("tally_id")

        show_inactive = self.request.GET.get(
            show_inactive_query_param, "false"
        )
        if format_ == "csv":
            form_list = ResultForm.forms_in_state(
                FormState.UNSUBMITTED, tally_id=tally_id
            )
            if not show_inactive or show_inactive.lower() != "true":
                form_list = form_list.filter(ballot__active=True)
            return render_to_csv_response(form_list)

        query_param_string = self.request.GET.urlencode()
        remote_data_url = reverse(
            "form-not-received-data", kwargs={"tally_id": tally_id}
        )
        if query_param_string:
            remote_data_url = f"{remote_data_url}?{query_param_string}"

        return self.render_to_response(
            self.get_context_data(
                header_text=_("Forms Not Received"),
                custom=True,
                remote_url=remote_data_url,
                tally_id=tally_id,
                export_file_name="forms-not-received-list",
                error_message="",
                show_create_form_button=False,
                show_inactive=show_inactive,
            )
        )


class FormNotReceivedDataView(FormListDataView):
    def filter_queryset(self, qs):
        show_inactive = self.request.GET.get(show_inactive_query_param)
        tally_id = self.kwargs.get("tally_id")
        keyword = self.request.POST.get("search[value]")

        qs = ResultForm.forms_in_state(
            FormState.UNSUBMITTED, tally_id=tally_id
        )

        # Apply active ballot filter
        if not show_inactive or show_inactive.lower() != "true":
            qs = qs.filter(ballot__active=True)

        if keyword:
            # Get matching FormState enum values for case-insensitive search
            matching_states = get_matching_enum_values(FormState, keyword)
            form_state_q = (
                Q(form_state__in=matching_states) if matching_states else Q()
            )

            qs = qs.filter(
                form_state_q
                | Q(barcode__icontains=keyword)
                | Q(center__code__contains=keyword)
                | Q(center__office__region__name__icontains=keyword)
                | Q(center__office__name__icontains=keyword)
                | Q(center__office__number__contains=keyword)
                | Q(station_number__contains=keyword)
                | Q(ballot__number__contains=keyword)
            )
        return qs


class FormsForRaceView(FormListView):
    group_require = groups.SUPER_ADMINISTRATOR

    def get(self, *args, **kwargs):
        ballot = kwargs.get("ballot")
        tally_id = kwargs.get("tally_id")

        return self.render_to_response(
            self.get_context_data(
                header_text=_("Forms for Race %(ballot)s")
                % {"ballot": ballot},
                none=True,
                tally_id=tally_id,
                remote_url=reverse(
                    "forms-for-race-data", args=[tally_id, ballot]
                ),
            )
        )


def get_result_forms(request):
    """
    Builds a json object of result forms.

    :param request: The request object containing the tally id.

    returns: A JSON response of result forms
    """
    tally_id = json.loads(request.GET.get("data")).get("tally_id")
    station_id_query = Subquery(
        Station.objects.filter(
            tally__id=tally_id,
            center__code=OuterRef("center__code"),
            station_number=OuterRef("station_number"),
        ).values("id")[:1],
        output_field=IntegerField(),
    )

    form_list = (
        ResultForm.objects.filter(tally__id=tally_id)
        .annotate(
            center_code=F("center__code"),
            center_name=F("center__name"),
            office_name=F("center__office__name"),
            office_number=F("center__office__number"),
            region_id=F("center__office__region__id"),
            region_name=F("center__office__region__name"),
            election_level=F("ballot__electrol_race__election_level"),
            sub_race=F("ballot__electrol_race__ballot_name"),
            ballot_number=F("ballot__number"),
            sub_con_name=F("center__sub_constituency__name"),
            sub_con_code=F("center__sub_constituency__code"),
            station_id=station_id_query,
        )
        .values(
            "id",
            "tally_id",
            "barcode",
            "station_id",
            "station_number",
            "center_name",
            "center_code",
            "office_id",
            "office_name",
            "office_number",
            "region_id",
            "region_name",
            "form_state",
            "election_level",
            "sub_race",
            "ballot_number",
            "sub_con_name",
            "sub_con_code",
        )
    )

    for form in form_list:
        if isinstance(form["form_state"], FormState):
            form["form_state"] = form["form_state"].label

    return JsonResponse(
        data={"data": list(form_list), "created_at": timezone.now()},
        safe=False,
    )
