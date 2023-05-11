from collections import defaultdict
from urllib.parse import urlencode

from django.db.models.deletion import ProtectedError
from django.core.exceptions import SuspiciousOperation
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Func, Q, F
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.edit import UpdateView, DeleteView, CreateView
from django.views.generic import FormView, TemplateView
from django.utils.translation import gettext_lazy as _
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.contrib import messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse

from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.disable_entity_form import DisableEntityForm
from tally_ho.apps.tally.forms.remove_center_form import RemoveCenterForm
from tally_ho.apps.tally.forms.remove_station_form import RemoveStationForm
from tally_ho.apps.tally.forms.quarantine_form import QuarantineCheckForm
from tally_ho.apps.tally.forms.edit_center_form import EditCenterForm
from tally_ho.apps.tally.forms.create_center_form import CreateCenterForm
from tally_ho.apps.tally.forms.create_station_form import CreateStationForm
from tally_ho.apps.tally.forms.create_race_form import CreateRaceForm
from tally_ho.apps.tally.forms.edit_ballot_form import EditBallotForm
from tally_ho.apps.tally.forms.edit_station_form import EditStationForm
from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditUserProfileForm,
)
from tally_ho.apps.tally.forms.create_result_form import CreateResultForm
from tally_ho.apps.tally.forms.edit_result_form import EditResultForm
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.views.constants import (
    race_type_query_param,
    sub_con_code_query_param,
    pending_at_state_query_param, at_state_query_param
)
from tally_ho.libs.models.enums.audit_resolution import \
    AuditResolution
from tally_ho.libs.models.enums.form_state import (
    FormState, un_processed_states_at_state
)
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.collections import flatten
from tally_ho.libs.utils.active_status import (
    disable_enable_entity,
    disable_enable_race,
    disable_enable_candidate,
)
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale
)
from tally_ho.libs.views import mixins
from tally_ho.libs.views.exports import (
    get_result_export_response,
    valid_ballots,
    distinct_forms,
    SPECIAL_BALLOTS,
)
from tally_ho.libs.views.pagination import paging
from tally_ho.libs.views.session import session_matches_post_result_form


def duplicates(qs, tally_id=None):
    """Build a list of result forms that are duplicates considering only forms
    that are not unsubmitted.

    :returns: A list of result forms in the system that are duplicates.
    """
    dupes = ResultForm.objects.values(
        'center', 'ballot', 'station_number', 'tally__id').annotate(
        Count('id')).order_by().filter(id__count__gt=1).filter(
        center__isnull=False,
        ballot__isnull=False,
        station_number__isnull=False,
        tally__id=tally_id,
    ).exclude(form_state=FormState.UNSUBMITTED)

    pks = flatten([map(lambda x: x['id'], ResultForm.objects.filter(
        center=item['center'],
        ballot=item['ballot'],
        station_number=item['station_number'],
        tally__id=item['tally__id'],
    ).values('id')) for item in dupes])

    return qs.filter(pk__in=pks)


def clearance(tally_id=None):
    """Build a list of result forms that are in clearance state considering
    only forms that are not unsubmitted.

    :returns: A list of result forms in the system that are in clearance state.
    """

    return ResultForm.objects.filter(form_state=FormState.CLEARANCE,
                                     tally__id=tally_id)


def audit(tally_id=None):
    """Build a list of result forms that are in audit pending state
    considering only forms that are not unsubmitted.

    :returns: A list of result forms in the system that are in audit pending
        state.
    """

    return ResultForm.objects.filter(form_state=FormState.AUDIT,
                                     tally__id=tally_id)


def get_results_duplicates(tally_id):
    complete_barcodes = []

    for ballot in valid_ballots(tally_id):
        forms = distinct_forms(ballot, tally_id)
        final_forms = ResultForm.forms_in_state(
            FormState.ARCHIVED, pks=[r.pk for r in forms], tally_id=tally_id)

        if not SPECIAL_BALLOTS or ballot.number in SPECIAL_BALLOTS:
            complete_barcodes.extend([r.barcode for r in final_forms])

    result_forms = ResultForm.objects \
        .select_related().filter(barcode__in=complete_barcodes,
                                 tally__id=tally_id)

    center_to_votes = defaultdict(list)
    center_to_forms = defaultdict(list)

    result_forms_founds = []

    for result_form in result_forms:
        # build list of votes for this barcode
        vote_list = ()

        for candidate in result_form.candidates:
            votes = candidate.num_votes(result_form)
            vote_list += (votes,)

        # store votes for this forms center
        center = result_form.center
        center_to_votes[center.code].append(vote_list)
        center_to_forms[center.code].append(result_form)

    for code, vote_lists in center_to_votes.items():
        votes_cast = sum([sum(vote) for vote in vote_lists]) > 0
        num_vote_lists = len(vote_lists)
        num_distinct_vote_lists = len(set(vote_lists))

        if votes_cast and num_distinct_vote_lists < num_vote_lists:

            for i, form in enumerate(center_to_forms[code]):
                vote_list = vote_lists[i]
                votes_cast = sum(vote_list) > 0
                other_vote_lists = vote_lists[:i] + vote_lists[i + 1:]

                if votes_cast and vote_list in other_vote_lists:
                    form.results_duplicated = vote_list
                    result_forms_founds.append(form)

    return result_forms_founds


def get_result_form_with_duplicate_results(
        ballot=None,
        tally_id=None,
        qs=None):
    """Build a list of result forms sorted by ballot of results forms for
    which there are more than 1 result form in the same ballot with the same
    number of votes per candidate, and the `duplicate_reviewed`
    column is false.

    :returns A list of result forms in the system with duplicate results.
    """
    qs = ResultForm.objects.filter(tally_id=tally_id) if not qs else qs
    result_form_ids = qs.exclude(results=None).values(
        'ballot',
        'results__votes',
        'results__candidate') \
        .annotate(ids=ArrayAgg('id')) \
        .annotate(duplicate_count=Count('id')) \
        .annotate(ids=Func('ids', function='unnest')) \
        .filter(
        duplicate_count__gt=1,
        duplicate_reviewed=False
    ).values_list('ids', flat=True).distinct()

    results_form_duplicates = \
        qs.filter(id__in=result_form_ids).order_by('ballot')

    if ballot:
        results_form_duplicates = results_form_duplicates.filter(ballot=ballot)

    return results_form_duplicates


class TalliesView(LoginRequiredMixin,
                  mixins.GroupRequiredMixin,
                  TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/tallies.html"

    def get(self, request, *args, **kwargs):
        try:
            userprofile = request.user.userprofile
            kwargs['tallies'] = userprofile.administrated_tallies.all()
        except UserProfile.DoesNotExist:
            kwargs['tallies'] = Tally.objects.all()
        return super(TalliesView, self).get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.TallyAccessMixin,
                    TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/home.html"

    def get(self, *args, **kwargs):
        group_logins = [g.lower().replace(' ', '_') for g in groups.GROUPS]
        kwargs['groups'] = group_logins
        kwargs['intake_clerk'] = groups.INTAKE_CLERK
        kwargs['intake_supervisor'] = groups.INTAKE_SUPERVISOR
        kwargs['clearance_clerk'] = groups.CLEARANCE_CLERK
        kwargs['clearance_supervisor'] = groups.CLEARANCE_SUPERVISOR
        kwargs['data_entry_1_clerk'] = groups.DATA_ENTRY_1_CLERK
        kwargs['data_entry_2_clerk'] = groups.DATA_ENTRY_2_CLERK
        kwargs['corrections_clerk'] = groups.CORRECTIONS_CLERK
        kwargs['quality_control_clerk'] = groups.QUALITY_CONTROL_CLERK
        kwargs['quality_control_supervisor'] = \
            groups.QUALITY_CONTROL_SUPERVISOR
        kwargs['audit_clerk'] = groups.AUDIT_CLERK
        kwargs['audit_supervisor'] = groups.AUDIT_SUPERVISOR

        return self.render_to_response(self.get_context_data(**kwargs))


class CreateResultFormView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.TallyAccessMixin,
                           mixins.ReverseSuccessURLMixin,
                           SuccessMessageMixin,
                           CreateView):
    model = ResultForm
    form_class = CreateResultForm
    group_required = [groups.SUPER_ADMINISTRATOR,
                      groups.CLEARANCE_CLERK,
                      groups.CLEARANCE_SUPERVISOR]
    template_name = 'super_admin/form.html'
    clearance_result_form = False
    barcode = None

    def get_initial(self):
        initial = super(CreateResultFormView, self).get_initial()
        tally_id = int(self.kwargs.get('tally_id'))
        self.barcode = self.model.generate_barcode(tally_id)
        initial['tally'] = tally_id
        initial['barcode'] = self.barcode
        initial['created_user'] = self.request.user.userprofile
        initial['form_state'] = FormState.CLEARANCE
        if self.clearance_result_form:
            self.success_url = 'clearance'
        else:
            self.success_url = 'form-list'
        return initial

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(CreateResultFormView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['barcode'] = self.barcode
        if self.clearance_result_form:
            context['title'] = _(u'Clearance: New Result Form')
            context['route_name'] = 'clearance'
        else:
            context['title'] = _(u'New Form')
            context['route_name'] = 'form-list'

        return context

    def form_valid(self, form):
        tally_id = self.kwargs.get('tally_id')
        self.initial = {
            'tally_id': tally_id,
        }
        tally = Tally.objects.get(id=tally_id)
        result_form = ResultForm.objects.create(
            barcode=form.data['barcode'],
            form_state=form.data['form_state'],
            tally=tally)
        self.request.session['result_form'] = result_form.pk
        post_data = self.request.POST.copy()
        post_data['result_form'] = self.request.session['result_form']
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = ResultForm.objects.get(pk=pk)

        if result_form.center or result_form.station_number \
                or result_form.ballot or result_form.office:
            # We are writing a form we should not be, bail out.
            del self.request.session['result_form']
            return redirect(self.success_url, tally_id=tally_id)

        form = CreateResultForm(post_data,
                                instance=result_form,
                                initial=self.initial)
        form.save()
        self.success_message = _(
            u"Successfully Created form %(form)s"
            % {'form': form.data['barcode']})

        return super(CreateResultFormView, self).form_valid(form)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')

        return reverse(self.success_url, kwargs={'tally_id': tally_id})


class EditResultFormView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
                         mixins.ReverseSuccessURLMixin,
                         SuccessMessageMixin,
                         UpdateView):
    model = ResultForm
    form_class = EditResultForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'super_admin/edit_result_form.html'
    success_message = _(u'Form Successfully Updated')

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(EditResultFormView, self).get_context_data(**kwargs)
        context['barcode'] = self.object.barcode
        context['station_number'] = self.object.station_number
        context['form_state'] = self.object.form_state.name
        context['tally_id'] = tally_id

        return context

    def get_object(self):
        tally_id = self.kwargs.get('tally_id')
        form_id = self.kwargs.get('form_id')

        return get_object_or_404(ResultForm, tally__id=tally_id, id=form_id)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')
        form_id = self.kwargs.get('form_id')

        return reverse('update-form',
                       kwargs={'tally_id': tally_id, 'form_id': form_id})


class RemoveResultFormConfirmationView(LoginRequiredMixin,
                                       mixins.GroupRequiredMixin,
                                       mixins.TallyAccessMixin,
                                       mixins.ReverseSuccessURLMixin,
                                       SuccessMessageMixin,
                                       DeleteView):
    model = ResultForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_result_form_confirmation.html"
    success_message = _(u'Form Successfully Deleted')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        context['next'] = request.META.get('HTTP_REFERER', None)
        context['tally_id'] = kwargs.get('tally_id')

        return self.render_to_response(context)

    def get_object(self, queryset=None):
        return ResultForm.objects.get(id=self.kwargs['form_id'],
                                      tally__id=self.kwargs['tally_id'])

    def post(self, request, *args, **kwargs):
        self.tally_id = self.kwargs['tally_id']
        next_url = request.POST.get('next', None)

        if 'abort_submit' in request.POST:
            return redirect(next_url, tally_id=self.kwargs['tally_id'])
        else:
            try:
                messages.add_message(
                    self.request, messages.INFO, self.success_message)
                return super(
                    RemoveResultFormConfirmationView,
                    self).post(request, *args, **kwargs)
            except ProtectedError:
                barcode = self.get_object().barcode
                request.session['error_message'] = \
                    f"Form {barcode} is tied to 1 or more object in the system"
                return redirect(
                    next_url,
                    tally_id=self.kwargs['tally_id'])

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')

        return reverse('form-list', kwargs={'tally_id': tally_id})


class FormProgressView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_progress.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-progress-data',
                               kwargs={'tally_id': tally_id}),
            languageDE=language_de,
            tally_id=tally_id))


class FormProgressByFormStateView(LoginRequiredMixin,
                                  mixins.GroupRequiredMixin,
                                  mixins.TallyAccessMixin,
                                  TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_progress_by_form_state.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        language_de = get_datatables_language_de_from_locale(self.request)
        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-progress-by-form-state-data',
                               kwargs={'tally_id': tally_id}),
            languageDE=language_de,
            tally_id=tally_id))


class DuplicateResultTrackingView(LoginRequiredMixin,
                                  mixins.GroupRequiredMixin,
                                  mixins.TallyAccessMixin,
                                  TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/duplicate_result_tracking.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']

        return self.render_to_response(self.get_context_data(
            duplicate_results=get_result_form_with_duplicate_results(
                tally_id=tally_id),
            tally_id=tally_id))


class DuplicateResultFormView(LoginRequiredMixin,
                              mixins.GroupRequiredMixin,
                              mixins.TallyAccessMixin,
                              SuccessMessageMixin,
                              TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/duplicate_result_form.html"
    success_url = "duplicate-result-tracking"

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        barcode = kwargs['barcode']
        ballot_id = kwargs['ballot_id']
        result_form = ResultForm.objects.get(
            barcode=barcode, tally_id=tally_id)
        results = Result.objects.filter(result_form=result_form.id)

        return self.render_to_response(self.get_context_data(
            results_form_duplicates=get_result_form_with_duplicate_results(
                ballot=ballot_id,
                tally_id=tally_id),
            results=results,
            tally_id=tally_id,
            ballot_id=ballot_id,
            header_text="Form " + str(barcode)))

    def post(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        ballot_id = kwargs['ballot_id']
        post_data = self.request.POST
        results_form_duplicates = get_result_form_with_duplicate_results(
            ballot=ballot_id,
            tally_id=tally_id)

        if 'duplicate_reviewed' in post_data:
            for results_form_duplicate in results_form_duplicates:
                results_form_duplicate.duplicate_reviewed = True
                results_form_duplicate.save()

            self.success_message = _(
                u"Successfully marked forms as duplicate reviewed")

            messages.add_message(
                self.request, messages.INFO, self.success_message)

            return redirect(self.success_url, tally_id=tally_id)
        elif 'send_clearance' in post_data:
            pk = post_data.get('result_form')
            result_form = get_object_or_404(
                ResultForm, pk=pk, tally__id=tally_id)
            if result_form.form_state != FormState.ARCHIVED:
                result_form.duplicate_reviewed = True
                result_form.form_state = FormState.CLEARANCE
                result_form.save()

                self.success_message = \
                    _(u"Form successfully sent to clearance")

                messages.add_message(
                    self.request, messages.INFO, self.success_message)

                return redirect(self.success_url, tally_id=tally_id)
            else:
                messages.error(
                    self.request,
                    _(u"Archived form can not be sent to clearance."))
                return HttpResponseRedirect(self.request.path_info)
        elif 'send_all_clearance' in post_data:
            archived_forms_barcodes = []
            for results_form_duplicate in results_form_duplicates:
                if results_form_duplicate.form_state != FormState.ARCHIVED:
                    results_form_duplicate.duplicate_reviewed = True
                    results_form_duplicate.form_state = FormState.CLEARANCE
                    results_form_duplicate.save()
                else:
                    archived_forms_barcodes.append(
                        results_form_duplicate.barcode)

            if archived_forms_barcodes:
                messages.error(
                    self.request,
                    _(u"Archived form(s) (%s) can not be sent to clearance.") %
                    (', '.join(archived_forms_barcodes)))
                return HttpResponseRedirect(self.request.path_info)
            else:
                self.success_message = _(
                    u"All forms successfully sent to clearance")

                messages.add_message(
                    self.request, messages.INFO, self.success_message)

                return redirect(self.success_url, tally_id=tally_id)

        else:
            raise SuspiciousOperation('Unknown POST response type')


class FormDuplicatesView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
                         TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_duplicates.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-duplicates-data',
                               kwargs={'tally_id': tally_id}),
            languageDE=language_de,
            tally_id=tally_id))


class FormClearanceView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_clearance.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-clearance-data',
                               kwargs={'tally_id': tally_id}),
            languageDE=language_de,
            tally_id=tally_id))


class FormAuditView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.TallyAccessMixin,
                    TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_audit.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        language_de = get_datatables_language_de_from_locale(self.request)

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-audit-data',
                               kwargs={'tally_id': tally_id}),
            languageDE=language_de,
            tally_id=tally_id))


class FormResultsDuplicatesView(LoginRequiredMixin,
                                mixins.GroupRequiredMixin,
                                mixins.TallyAccessMixin,
                                TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_results_duplicates.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-duplicates-data',
                               kwargs={'tally_id': tally_id}),
            tally_id=tally_id))


class FormProgressDataView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.TallyAccessMixin,
                           BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    columns = (
        'barcode',
        'center.code',
        'station_number',
        'ballot.number',
        'center.office.name',
        'center.office.number',
        'ballot.race_type',
        'form_state',
        'rejected_count',
        'modified_date_formatted',
    )

    def filter_queryset(self, qs):
        tally_id = self.kwargs['tally_id']

        qs = qs.filter(tally__id=tally_id)
        return qs.exclude(form_state=FormState.UNSUBMITTED)


class FormProgressByFormStateDataView(LoginRequiredMixin,
                                      mixins.GroupRequiredMixin,
                                      mixins.TallyAccessMixin,
                                      BaseDatatableView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    columns = (
        'sub_con_code',
        'race_type',
        'total_forms',
        'unsubmitted',
        ('intake', 'intake_unprocessed'),
        ('data_entry_1', 'data_entry_1_unprocessed'),
        ('data_entry_2', 'data_entry_2_unprocessed'),
        ('correction', 'correction_unprocessed'),
        ('quality_control', 'quality_control_unprocessed'),
        ('archived', 'archived_unprocessed'),
        'clearance',
        'audit'
    )

    def filter_queryset(self, qs):
        tally_id = self.kwargs['tally_id']
        keyword = self.request.POST.get('search[value]')
        qs = qs.filter(
            tally__id=tally_id,
            center__sub_constituency__code__isnull=False)

        if keyword:
            qs = qs.filter(
                Q(center__sub_constituency__code__contains=keyword))

        count_by_form_state_queries = {}
        for state in FormState.__publicMembers__():
            count_by_form_state_queries[state.name.lower()] \
                = Count('barcode', filter=Q(
                    form_state=state)
                    )
            unprocessed_states = un_processed_states_at_state(state)
            if unprocessed_states:
                count_by_form_state_queries[
                    f"{state.name.lower()}_unprocessed"] = Count(
                    'barcode', filter=Q(form_state__in=unprocessed_states))

        qs = qs.annotate(
            sub_con_code=F("center__sub_constituency__code")).values(
            'sub_con_code') \
            .annotate(
            race_type=F("ballot__race_type"),
            total_forms=Count("race_type"),
            **count_by_form_state_queries)
        return qs

    def render_column(self, row, column):
        tally_id = self.kwargs.get('tally_id')
        sub_con_code = row["sub_con_code"]
        if column in self.columns:
            column_val = None
            race_type = row["race_type"].name.lower()
            if isinstance(column, tuple) is False and row[column] != 0 and\
                column in ["unsubmitted", "clearance", "audit"]:
                params = {race_type_query_param: race_type,
                         sub_con_code_query_param: sub_con_code,
                        at_state_query_param: column}
                query_param_string = urlencode(params)
                remote_data_url = reverse(
                    'form-list',
                    kwargs={'tally_id': tally_id})
                if query_param_string:
                    remote_data_url = f"{remote_data_url}?{query_param_string}"
                column_val = str('<span>'
                                f'<a href={remote_data_url} target="blank">'
                                f'{row[column]}</a></span>')
            elif isinstance(column, tuple) and len(column) == 2:
                remote_data_url = reverse(
                    'form-list',
                    kwargs={'tally_id': tally_id})
                current_state_col, unprocessed_col = column
                current_state_form_count = row[current_state_col]
                unprocessed_count = row[unprocessed_col]
                current_state_column_val = f'<span>{current_state_form_count}'
                unprocessed_column_val = f'{unprocessed_count}</span>'
                if current_state_form_count > 0:
                    current_state_form_url_params =\
                        {race_type_query_param: race_type,
                            sub_con_code_query_param: sub_con_code,
                        at_state_query_param: column[0]}
                    current_state_form_query_param_string =\
                        urlencode(current_state_form_url_params)
                    current_state_form_remote_data_url =\
                            str(f"{remote_data_url}?"
                                f"{current_state_form_query_param_string}")
                    current_state_column_val =\
                        str('<span>'
                                f'<a href='
                                f'{current_state_form_remote_data_url} '
                                'target="blank">'
                                f'{current_state_form_count}</a></span>')
                if unprocessed_count > 0:
                    unprocessed_forms_url_params =\
                        {race_type_query_param: race_type,
                            sub_con_code_query_param: sub_con_code,
                        pending_at_state_query_param: column[0]}
                    unprocessed_forms_query_param_string =\
                        urlencode(unprocessed_forms_url_params)
                    unprocessed_remote_data_url =\
                            str(f'{remote_data_url}?'
                                f'{unprocessed_forms_query_param_string}')
                    unprocessed_column_val =\
                            str('<span>'
                                f'<a href={unprocessed_remote_data_url} '
                                'target="blank">'
                                f'{unprocessed_count}</a></span>')
                column_val =\
                    current_state_column_val + ' / ' + unprocessed_column_val
            else:
                column_val = row[column]
            if column == 'race_type':
                column_val = row[column].name
            return str('<td class="center">'
                       f'{column_val}</td>')

        else:
            return super(
                FormProgressByFormStateDataView, self).render_column(
                row, column)


class FormAuditDataView(FormProgressDataView):
    columns = (
        'barcode',
        'center.code',
        'station_number',
        'ballot.number',
        'center.office.name',
        'center.office.number',
        'ballot.race_type',
        'form_state',
        'rejected_count',
        'modified_date_formatted',
        'audit_recommendation',
    )

    def filter_queryset(self, qs):
        return super().filter_queryset(qs).filter(form_state=FormState.AUDIT)


class FormDuplicatesDataView(FormProgressDataView):
    def filter_queryset(self, qs):
        tally_id = self.kwargs['tally_id']

        return duplicates(super().filter_queryset(qs), tally_id)


class FormClearanceDataView(FormProgressDataView):
    columns = (
        'barcode',
        'center.code',
        'station_number',
        'ballot.number',
        'center.office.name',
        'center.office.number',
        'ballot.race_type',
        'form_state',
        'rejected_count',
        'modified_date_formatted',
        'clearance_recommendation'
    )

    def filter_queryset(self, qs):
        return super().filter_queryset(qs).filter(clearances__active=True)


class FormActionView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     mixins.ReverseSuccessURLMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_action.html"
    success_url = 'form-action-view'

    def get(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        audits = Audit.objects.filter(
            active=True,
            reviewed_supervisor=True,
            resolution_recommendation=AuditResolution.
            MAKE_AVAILABLE_FOR_ARCHIVE,
            result_form__tally__id=tally_id).all()

        return self.render_to_response(self.get_context_data(
            audits=audits,
            tally_id=tally_id))

    def post(self, *args, **kwargs):
        tally_id = kwargs['tally_id']
        post_data = self.request.POST
        pk = post_data.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        self.request.session['result_form'] = result_form.pk

        if 'review' in post_data:
            return redirect('audit-review', tally_id=tally_id)
        elif 'confirm' in post_data:
            result_form.reject()
            result_form.skip_quarantine_checks = True
            result_form.save()

            audit = result_form.audit
            audit.active = False
            audit.save()

            return redirect(self.success_url, tally_id=tally_id)
        else:
            raise SuspiciousOperation('Unknown POST response type')


class CreateCenterView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       mixins.ReverseSuccessURLMixin,
                       SuccessMessageMixin,
                       CreateView):
    model = Center
    form_class = CreateCenterForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'super_admin/form.html'

    def get_initial(self):
        initial = super(CreateCenterView, self).get_initial()
        initial['tally'] = int(self.kwargs.get('tally_id'))

        return initial

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(CreateCenterView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['title'] = _(u'New Center')
        context['route_name'] = 'center-list'

        return context

    def form_valid(self, form):
        center = form.save()
        self.success_message = _(
            u"Successfully Created Center %(center)s"
            % {'center': center.code})

        return super(CreateCenterView, self).form_valid(form)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')

        return reverse('center-list', kwargs={'tally_id': tally_id})


class ResultExportView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/result_export.html"

    def get(self, *args, **kwargs):
        report = kwargs.get('report')
        tally_id = kwargs.get('tally_id')
        if report:
            return get_result_export_response(report, int(tally_id))
        return super(ResultExportView, self).get(*args, **kwargs)


class RemoveCenterView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       mixins.ReverseSuccessURLMixin,
                       SuccessMessageMixin,
                       FormView):
    form_class = RemoveCenterForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_center.html"
    success_message = _(u"Center Successfully Removed.")

    def get_context_data(self, **kwargs):
        context = super(RemoveCenterView, self).get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')

        return context

    def get_initial(self):
        initial = super(RemoveCenterView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            center = form.save()
            self.success_message = _(
                u"Successfully removed center %(center)s"
                % {'center': center.code})
            self.success_url = reverse('remove-center-confirmation',
                                       kwargs={'center_code': center.code,
                                               'tally_id': center.tally.id})
            return redirect(self.success_url)
        return self.form_invalid(form)


class RemoveCenterConfirmationView(LoginRequiredMixin,
                                   mixins.GroupRequiredMixin,
                                   mixins.TallyAccessMixin,
                                   mixins.ReverseSuccessURLMixin,
                                   SuccessMessageMixin,
                                   DeleteView):
    model = Center
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_center_confirmation.html"
    success_message = _(u"Center Successfully Removed.")
    slug_url_kwarg = 'center_code'
    success_url = 'center-list'
    slug_field = 'code'
    tally_id = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        context['next'] = request.META.get('HTTP_REFERER', None)
        context['tally_id'] = kwargs.get('tally_id')

        return self.render_to_response(context)

    def get_object(self, queryset=None):
        return Center.objects.get(code=self.kwargs['center_code'],
                                  tally__id=self.kwargs['tally_id'])

    def post(self, request, *args, **kwargs):
        self.tally_id = self.kwargs['tally_id']
        next_url = request.POST.get('next', None)

        if 'abort_submit' in request.POST:
            return redirect(next_url, tally_id=self.kwargs['tally_id'])
        else:
            try:
                return super(RemoveCenterConfirmationView, self).post(request,
                                                                      *args,
                                                                      **kwargs)
            except ProtectedError:
                request.session['error_message'] = \
                    str(_(u"This center is tied to 1 or more stations"))
                return redirect(
                    next_url,
                    tally_id=self.kwargs['tally_id'])


class EditCenterView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     mixins.ReverseSuccessURLMixin,
                     SuccessMessageMixin,
                     UpdateView):
    model = Center
    form_class = EditCenterForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'super_admin/edit_center.html'
    success_message = _(u'Center Successfully Updated')

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(EditCenterView, self).get_context_data(**kwargs)
        context['center_code'] = self.kwargs.get('center_code')
        error_message = self.request.session.get('error_message')
        context['tally_id'] = tally_id
        context['is_active'] = self.object.active
        context['comments'] = self.object.comments.filter(tally__id=tally_id)

        if error_message:
            del self.request.session['error_message']
            context['error_message'] = error_message

        return context

    def get_object(self):
        tally_id = self.kwargs.get('tally_id')
        center_code = self.kwargs.get('center_code')

        return get_object_or_404(Center, tally__id=tally_id, code=center_code)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')

        return reverse('center-list', kwargs={'tally_id': tally_id})


class DisableEntityView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        mixins.ReverseSuccessURLMixin,
                        SuccessMessageMixin,
                        FormView):
    form_class = DisableEntityForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/disable_entity.html"
    success_url = 'center-list'

    def get(self, *args, **kwargs):
        station_number = kwargs.get('station_number')
        center_code = kwargs.get('center_code')
        tally_id = kwargs.get('tally_id')

        entity_name = u'Center' if not station_number else u'Station'

        self.initial = {
            'tally_id': tally_id,
            'center_code_input': center_code,
            'station_number_input': station_number
        }
        self.success_message = _(u"%s Successfully Disabled.") % entity_name
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, entity=entity_name.lower(),
                                  entityName=entity_name,
                                  tally_id=tally_id))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        tally_id = kwargs.get('tally_id')

        if form.is_valid():
            entity = form.save()

            if isinstance(entity, Center):
                self.success_message = _(
                    u"Successfully disabled center %(center)s"
                    % {'center': entity.code})
            else:
                self.success_message = _(
                    u"Successfully disabled station %(station_number)s"
                    % {'station_number': entity.station_number})

            return redirect(self.success_url, tally_id=tally_id)

        return self.render_to_response(self.get_context_data(
            form=form, tally_id=tally_id))


class EnableEntityView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       mixins.ReverseSuccessURLMixin,
                       SuccessMessageMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    success_url = 'center-list'

    def get(self, *args, **kwargs):
        station_number = kwargs.get('station_number')
        center_code = kwargs.get('center_code')
        tally_id = kwargs.get('tally_id')

        entityName = u'Center' if not station_number else u'Station'

        self.success_message = _(u"%s Successfully enabled.") % entityName

        disable_enable_entity(center_code, station_number, tally_id=tally_id)

        messages.add_message(self.request, messages.INFO, self.success_message)

        return redirect(self.success_url, tally_id=tally_id)


class CreateRaceView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     mixins.ReverseSuccessURLMixin,
                     SuccessMessageMixin,
                     CreateView):
    model = Ballot
    form_class = CreateRaceForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'super_admin/form.html'
    success_message = _(u'Race Successfully Created')

    def get_initial(self):
        initial = super(CreateRaceView, self).get_initial()
        initial['tally'] = int(self.kwargs.get('tally_id'))

        return initial

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(CreateRaceView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['title'] = _(u'New Race')
        context['route_name'] = 'races-list'

        return context

    def form_valid(self, form):
        form = CreateRaceForm(self.request.POST, self.request.FILES)
        form.save()

        return super(CreateRaceView, self).form_valid(form)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')

        return reverse('races-list', kwargs={'tally_id': tally_id})


class EditBallotView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.TallyAccessMixin,
                   mixins.ReverseSuccessURLMixin,
                   SuccessMessageMixin,
                   UpdateView):
    model = Ballot
    form_class = EditBallotForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'super_admin/edit_ballot.html'
    success_message = _(u'Ballot Successfully Updated')

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(EditBallotView, self).get_context_data(**kwargs)
        context['id'] = self.kwargs.get('id')
        context['tally_id'] = tally_id
        context['is_active'] = self.object.active
        context['comments'] = self.object.comments.filter(tally__id=tally_id)

        return context

    def get_object(self):
        tally_id = self.kwargs.get('tally_id')
        id = self.kwargs.get('id')

        return get_object_or_404(Ballot, tally__id=tally_id, id=id)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')
        id = self.kwargs.get('id')

        return reverse('edit-ballot', kwargs={'tally_id': tally_id, 'id': id})

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        race_id = kwargs.get('id')

        self.initial = {
            'tally_id': tally_id,
            'race_id': race_id,
        }

        return super(EditBallotView, self).get(*args, **kwargs)


class DisableRaceView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.TallyAccessMixin,
                      mixins.ReverseSuccessURLMixin,
                      SuccessMessageMixin,
                      FormView):
    form_class = DisableEntityForm
    group_required = groups.SUPER_ADMINISTRATOR
    tally_id = None
    template_name = "super_admin/disable_entity.html"
    success_url = 'races-list'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        race_id = kwargs.get('race_id')

        self.initial = {
            'tally_id': tally_id,
            'center_code_input': None,
            'station_number_input': None,
            'race_id_input': race_id,
        }

        self.success_message = _(u"Race Successfully Disabled.")
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form,
                                  tally_id=tally_id))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        self.tally_id = self.kwargs['tally_id']

        if form.is_valid():
            form.save()

            self.success_message = _(u"Race Successfully disabled")

            return self.form_valid(form)

        return self.render_to_response(self.get_context_data(
            form=form, tally_id=self.tally_id))


class EnableRaceView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     mixins.ReverseSuccessURLMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    success_url = 'races-list'

    def get(self, *args, **kwargs):
        race_id = kwargs.get('race_id')
        tally_id = self.kwargs['tally_id']

        disable_enable_race(race_id)

        messages.add_message(self.request,
                             messages.INFO,
                             _(u"Race Successfully enabled."))

        return redirect(self.success_url, tally_id=tally_id)


class CreateStationView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        mixins.ReverseSuccessURLMixin,
                        SuccessMessageMixin,
                        FormView):
    model = Station
    form_class = CreateStationForm
    group_required = groups.SUPER_ADMINISTRATOR
    success_message = _(u"Station Successfully Created")
    template_name = 'super_admin/form.html'

    def get_initial(self):
        initial = super(CreateStationView, self).get_initial()
        initial['tally'] = int(self.kwargs.get('tally_id'))

        return initial

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')
        context = super(CreateStationView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['title'] = _(u'New Station')
        context['route_name'] = 'center-list'

        return context

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        tally_id = self.kwargs.get('tally_id')
        if form.is_valid():
            station = form.save()
            self.success_message = _(
                u"Successfully created station %(center)s"
                % {'center': station.center.code})
            messages.add_message(
                self.request, messages.INFO, self.success_message)
            self.success_url = reverse(
                'center-list', kwargs={'tally_id': tally_id})
            return redirect(self.success_url)
        return self.form_invalid(form)


class RemoveStationView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        mixins.ReverseSuccessURLMixin,
                        SuccessMessageMixin,
                        FormView):
    form_class = RemoveStationForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_station.html"
    success_message = _(u"Station Successfully Removed.")

    def get_context_data(self, **kwargs):
        context = super(RemoveStationView, self).get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')

        return context

    def get_initial(self):
        initial = super(RemoveStationView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            station = form.save()
            self.success_url = reverse(
                'remove-station-confirmation',
                kwargs={
                    'station_id': station.pk,
                    'tally_id': station.center.tally.id})
            return redirect(self.success_url)
        return self.form_invalid(form)


class QuarantineChecksListView(LoginRequiredMixin,
                               mixins.GroupRequiredMixin,
                               TemplateView):
    template_name = 'super_admin/quarantine_checks_list.html'
    group_required = groups.SUPER_ADMINISTRATOR

    def get_context_data(self, **kwargs):
        context = \
            super(QuarantineChecksListView, self).get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')

        return context

    def get(self, *args, **kwargs):
        all_checks = QuarantineCheck.objects.all().order_by('id')

        checks = paging(all_checks, self.request)

        return self.render_to_response(self.get_context_data(
            checks=checks))


class QuarantineChecksConfigView(LoginRequiredMixin,
                                 mixins.GroupRequiredMixin,
                                 mixins.ReverseSuccessURLMixin,
                                 UpdateView):
    template_name = 'super_admin/quarantine_checks_config.html'
    group_required = groups.SUPER_ADMINISTRATOR

    model = QuarantineCheck
    form_class = QuarantineCheckForm

    def get_context_data(self, **kwargs):
        context = \
            super(QuarantineChecksConfigView, self).get_context_data(**kwargs)
        context['tally_id'] = self.kwargs.get('tally_id')

        return context

    def get_object(self, queryset=None):
        obj = QuarantineCheck.objects.get(id=self.kwargs['checkId'])
        return obj

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')

        return reverse('quarantine-checks', kwargs={'tally_id': tally_id})


class RemoveStationConfirmationView(LoginRequiredMixin,
                                    mixins.GroupRequiredMixin,
                                    mixins.TallyAccessMixin,
                                    mixins.ReverseSuccessURLMixin,
                                    SuccessMessageMixin,
                                    DeleteView):
    model = Station
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_station_confirmation.html"
    success_url = 'center-list'
    success_message = _(u"Station Successfully Removed.")
    tally_id = None

    def delete(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        station_id = kwargs.get('station_id')

        self.object = self.get_object(station_id)
        success_url = self.get_success_url()

        self.object.delete()

        return redirect(success_url, tally_id=tally_id)

    def get(self, request, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        station_id = kwargs.get('station_id')

        self.object = self.get_object(station_id)
        context = self.get_context_data(object=self.object, tally_id=tally_id)
        context['next'] = request.META.get('HTTP_REFERER', None)

        return self.render_to_response(context)

    def get_object(self, station_id):
        return get_object_or_404(Station, pk=station_id)

    def post(self, request, *args, **kwargs):
        self.tally_id = self.kwargs.get('tally_id')
        station_id = self.kwargs.get('station_id')

        if 'abort_submit' in request.POST:
            next_url = request.POST.get('next', None)

            return redirect(next_url, tally_id=self.tally_id)
        else:
            try:
                station = self.get_object(station_id)
                self.success_message = _(
                    u"Successfully removed station %(station)s from "
                    u"center %(center)s." % {
                        'center': station.center.code,
                        'station': station.station_number
                    })
                messages.add_message(
                    self.request,
                    messages.INFO,
                    self.success_message
                )
            except Http404:
                pass
            return super(
                RemoveStationConfirmationView,
                self).post(request, *args, **kwargs)


class EditStationView(LoginRequiredMixin,
                      mixins.GroupRequiredMixin,
                      mixins.TallyAccessMixin,
                      mixins.ReverseSuccessURLMixin,
                      SuccessMessageMixin,
                      UpdateView):
    model = Station
    form_class = EditStationForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'super_admin/edit_station.html'
    success_message = _(u'Station Successfully Updated')

    def get_context_data(self, **kwargs):
        context = super(EditStationView, self).get_context_data(**kwargs)
        context['center_code'] = self.object.center.code
        context['sub_con'] = self.object.sub_constituency.code
        context['region'] = self.object.center.office.region.name
        context['station_number'] = self.object.station_number
        context['station_id'] = self.object.pk
        context['tally_id'] = self.kwargs.get('tally_id')
        context['is_active'] = self.object.active
        context['center_is_active'] = self.object.center.active
        context['comments'] = self.object.comments.all()

        return context

    def get_object(self):
        station_id = self.kwargs.get('station_id')

        return get_object_or_404(Station, pk=station_id)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id')

        return reverse('center-list', kwargs={'tally_id': tally_id})


class EnableCandidateView(LoginRequiredMixin,
                          mixins.GroupRequiredMixin,
                          mixins.TallyAccessMixin,
                          mixins.ReverseSuccessURLMixin,
                          SuccessMessageMixin,
                          TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    success_url = 'candidate-list'

    def get(self, *args, **kwargs):
        candidate_id = kwargs.get('candidateId')
        tally_id = kwargs.get('tally_id')

        self.success_message = _(u"Candidate successfully enabled.")

        disable_enable_candidate(candidate_id)

        return redirect(self.success_url, tally_id=tally_id)


class DisableCandidateView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.TallyAccessMixin,
                           mixins.ReverseSuccessURLMixin,
                           SuccessMessageMixin,
                           TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    success_url = 'candidate-list'

    def get(self, *args, **kwargs):
        candidate_id = kwargs.get('candidateId')
        tally_id = kwargs.get('tally_id')

        self.success_message = _(u"Candidate successfully disabled.")

        disable_enable_candidate(candidate_id)

        return redirect(self.success_url, tally_id=tally_id)


class EditUserView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.TallyAccessMixin,
                   mixins.ReverseSuccessURLMixin,
                   SuccessMessageMixin,
                   UpdateView):
    model = UserProfile
    form_class = EditUserProfileForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'tally_manager/edit_user_profile.html'
    slug_url_kwarg = 'user_id'
    slug_field = 'id'

    def get_initial(self):
        initial = super(EditUserView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')
        initial['role'] = self.kwargs.get('role', 'user')

        return initial

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        role = self.kwargs.get('role', 'user')
        context['is_admin'] = False
        context['tally_id'] = self.kwargs.get('tally_id')
        context['role'] = role
        referer_url = self.request.META.get('HTTP_REFERER', None)
        url_name = None
        url_param = None
        url_keyword = None

        try:
            int([param for param in referer_url.split('/') if param][-1])
        except ValueError:
            url_name = 'user-list'
            url_param = role
            url_keyword = 'role'
        else:
            url_name = 'user-tally-list'
            url_param = self.kwargs.get('tally_id')
            url_keyword = 'tally_id'
        finally:
            context['url_name'] = url_name
            context['url_param'] = url_param
            self.request.session['url_name'] = url_name
            self.request.session['url_param'] = url_param
            self.request.session['url_keyword'] = url_keyword

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

    def get_object(self, queryset=None):
        user = super(EditUserView, self).get_object(queryset)

        if not user.tally or user.tally.id != int(self.kwargs.get('tally_id')):
            raise Http404

        return user


class CreateUserView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     CreateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'tally_manager/edit_user_profile.html'
    model = UserProfile
    form_class = EditUserProfileForm

    def get_initial(self):
        initial = super(CreateUserView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def get_context_data(self, **kwargs):
        context = super(CreateUserView, self).get_context_data(**kwargs)
        role = self.kwargs.get('role', 'user')
        context['is_admin'] = False
        tally_id = self.kwargs.get('tally_id')
        context['tally_id'] = tally_id
        url_name = None
        url_param = None
        url_keyword = None

        if tally_id:
            url_name = 'user-tally-list'
            url_param = self.kwargs.get('tally_id')
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
