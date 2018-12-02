from collections import defaultdict

from django.core.exceptions import SuspiciousOperation
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.edit import UpdateView, DeleteView, CreateView
from django.views.generic import FormView, TemplateView
from django.utils.translation import ugettext_lazy as _
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.contrib import messages
from django.http import Http404
from django.urls import reverse

from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.disable_entity_form import DisableEntityForm
from tally_ho.apps.tally.forms.remove_center_form import RemoveCenterForm
from tally_ho.apps.tally.forms.remove_station_form import RemoveStationForm
from tally_ho.apps.tally.forms.quarantine_form import QuarantineCheckForm
from tally_ho.apps.tally.forms.edit_center_form import EditCenterForm
from tally_ho.apps.tally.forms.edit_race_form import EditRaceForm
from tally_ho.apps.tally.forms.edit_station_form import EditStationForm
from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditUserProfileForm,
)
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.enums.audit_resolution import\
    AuditResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.collections import flatten
from tally_ho.libs.utils.active_status import (
    disable_enable_entity,
    disable_enable_race,
    disable_enable_candidate,
)
from tally_ho.libs.views import mixins
from tally_ho.libs.views.exports import (
    get_result_export_response,
    valid_ballots,
    distinct_forms,
    SPECIAL_BALLOTS,
)
from tally_ho.libs.views.pagination import paging


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

    result_forms = ResultForm.objects\
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
        votes_cast = sum([sum(l) for l in vote_lists]) > 0
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

        return self.render_to_response(self.get_context_data(**kwargs))


class FormProgressView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_progress.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-progress-data',
                               kwargs={'tally_id': tally_id}),
            tally_id=tally_id))


class FormDuplicatesView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         mixins.TallyAccessMixin,
                         TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_duplicates.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-duplicates-data',
                               kwargs={'tally_id': tally_id}),
            tally_id=tally_id))


class FormClearanceView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.TallyAccessMixin,
                        TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_clearance.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-clearance-data',
                               kwargs={'tally_id': tally_id}),
            tally_id=tally_id))


class FormAuditView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    mixins.TallyAccessMixin,
                    TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_audit.html"

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')

        return self.render_to_response(self.get_context_data(
            remote_url=reverse('form-audit-data',
                               kwargs={'tally_id': tally_id}),
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
        'modified_date',
    )

    def filter_queryset(self, qs):
        tally_id = self.kwargs['tally_id']

        qs = qs.filter(tally__id=tally_id)
        return qs.exclude(form_state=FormState.UNSUBMITTED)


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
        'modified_date',
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
        'modified_date',
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

        if 'abort_submit' in request.POST:
            next_url = request.POST.get('next', None)

            return redirect(next_url, tally_id=self.kwargs['tally_id'])
        else:
            return super(RemoveCenterConfirmationView, self).post(request,
                                                                  *args,
                                                                  **kwargs)


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
        context = super(EditCenterView, self).get_context_data(**kwargs)
        context['center_code'] = self.kwargs.get('center_code', None)
        context['tally_id'] = self.kwargs.get('tally_id', None)
        context['is_active'] = self.object.active
        context['comments'] = self.object.comments.all()

        return context

    def get_object(self):
        tally_id = self.kwargs.get('tally_id', None)
        center_code = self.kwargs.get('center_code', None)

        return get_object_or_404(Center, tally__id=tally_id, code=center_code)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id', None)

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
        center_code = kwargs.get('center_code', None)
        tally_id = kwargs.get('tally_id', None)

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
        tally_id = kwargs.get('tally_id', None)

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
        center_code = kwargs.get('center_code', None)
        tally_id = kwargs.get('tally_id')

        entityName = u'Center' if not station_number else u'Station'

        self.success_message = _(u"%s Successfully enabled.") % entityName

        disable_enable_entity(center_code, station_number, tally_id=tally_id)

        messages.add_message(self.request, messages.INFO, self.success_message)

        return redirect(self.success_url, tally_id=tally_id)


class EditRaceView(LoginRequiredMixin,
                   mixins.GroupRequiredMixin,
                   mixins.TallyAccessMixin,
                   mixins.ReverseSuccessURLMixin,
                   SuccessMessageMixin,
                   UpdateView):
    model = Ballot
    form_class = EditRaceForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = 'super_admin/edit_race.html'
    success_message = _(u'Race Successfully Updated')

    def get_context_data(self, **kwargs):
        context = super(EditRaceView, self).get_context_data(**kwargs)
        context['id'] = self.kwargs.get('id', None)
        context['tally_id'] = self.kwargs.get('tally_id', None)
        context['is_active'] = self.object.active
        context['comments'] = self.object.comments.all()

        return context

    def get_object(self):
        tally_id = self.kwargs.get('tally_id', None)
        id = self.kwargs.get('id', None)

        return get_object_or_404(Ballot, tally__id=tally_id, id=id)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id', None)

        return reverse('race-list', kwargs={'tally_id': tally_id})


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
            self.success_message = _(
                u"Successfully removed station %(station)s from "
                u"center %(center)s." % {
                    'center': station.center.code,
                    'station': station.station_number
                })
            self.success_url = reverse(
                'remove-station-confirmation',
                kwargs={
                    'center_code': station.center_code,
                    'station_number': station.station_number,
                    'tally_id': station.center.tally.id})
            return redirect(self.success_url)
        return self.form_invalid(form)


class QuarantineChecksListView(LoginRequiredMixin,
                               mixins.GroupRequiredMixin,
                               TemplateView):
    template_name = 'super_admin/quarantine_checks_list.html'
    group_required = groups.SUPER_ADMINISTRATOR

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
    success_url = 'quarantine-checks'

    def get_object(self, queryset=None):
        obj = QuarantineCheck.objects.get(id=self.kwargs['checkId'])
        return obj


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
        center_code = kwargs.get('center_code', None)
        station_number = kwargs.get('station_number', None)
        tally_id = kwargs.get('tally_id', None)

        self.object = self.get_object(center_code, station_number, tally_id)
        success_url = self.get_success_url()

        self.object.delete()

        return redirect(success_url, tally_id=tally_id)

    def get(self, request, *args, **kwargs):
        center_code = kwargs.get('center_code', None)
        station_number = kwargs.get('station_number', None)
        tally_id = kwargs.get('tally_id', None)

        self.object = self.get_object(center_code, station_number, tally_id)
        context = self.get_context_data(object=self.object, tally_id=tally_id)
        context['next'] = request.META.get('HTTP_REFERER', None)

        return self.render_to_response(context)

    def get_object(self, center_code, station_number, tally_id):
        return get_object_or_404(Station, center__code=center_code,
                                 station_number=station_number,
                                 center__tally__id=tally_id)

    def post(self, request, *args, **kwargs):
        self.tally_id = self.kwargs['tally_id']

        if 'abort_submit' in request.POST:
            next_url = request.POST.get('next', None)

            return redirect(next_url, tally_id=self.tally_id)
        else:
            return super(RemoveStationConfirmationView, self).post(request,
                                                                   *args,
                                                                   **kwargs)


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
        context['center_code'] = self.kwargs.get('center_code', None)
        context['station_number'] = self.kwargs.get('station_number', None)
        context['tally_id'] = self.kwargs.get('tally_id', None)
        context['is_active'] = self.object.active
        context['center_is_active'] = self.object.center.active
        context['comments'] = self.object.comments.all()

        return context

    def get_object(self):
        tally_id = self.kwargs.get('tally_id', None)
        center_code = self.kwargs.get('center_code', None)
        station_number = self.kwargs.get('station_number', None)

        return get_object_or_404(Station,
                                 station_number=station_number,
                                 center__tally__id=tally_id,
                                 center__code=center_code)

    def get_success_url(self):
        tally_id = self.kwargs.get('tally_id', None)

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

        return initial

    def get_context_data(self, **kwargs):
        context = super(EditUserView, self).get_context_data(**kwargs)
        context['is_admin'] = False
        context['tally_id'] = self.kwargs.get('tally_id')

        return context

    def get_success_url(self):
        return reverse('user-tally-list',
                       kwargs={'tally_id': self.kwargs.get('tally_id')})

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
        context['is_admin'] = False
        context['tally_id'] = self.kwargs.get('tally_id')

        return context

    def get_success_url(self):
        return reverse('user-tally-list',
                       kwargs={'tally_id': self.kwargs.get('tally_id')})
