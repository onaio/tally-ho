from collections import defaultdict

from django.core.exceptions import SuspiciousOperation
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView
from django.utils.translation import ugettext_lazy as _
from eztables.views import DatatablesView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.remove_center_form import RemoveCenterForm
from tally_ho.apps.tally.forms.disable_entity_form import DisableEntityForm
from tally_ho.apps.tally.forms.remove_station_form import RemoveStationForm
from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.audit_resolution import\
    AuditResolution
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.collections import flatten
from tally_ho.libs.utils.functions import disableEnableEntity
from tally_ho.libs.views import mixins
from tally_ho.libs.views.exports import get_result_export_response,\
    valid_ballots, distinct_forms, SPECIAL_BALLOTS
from tally_ho.libs.views.pagination import paging


def duplicates():
    """Build a list of result forms that are duplicates considering only forms
    that are not unsubmitted.

    :returns: A list of result forms in the system that are duplicates.
    """
    dupes = ResultForm.objects.values(
        'center', 'ballot', 'station_number').annotate(
        Count('id')).order_by().filter(id__count__gt=1).filter(
        center__isnull=False, ballot__isnull=False,
        station_number__isnull=False).exclude(form_state=FormState.UNSUBMITTED)

    pks = flatten([map(lambda x: x['id'], ResultForm.objects.filter(
        center=item['center'], ballot=item['ballot'],
        station_number=item['station_number']).values('id'))
        for item in dupes])

    return ResultForm.objects.filter(pk__in=pks)


def get_results_duplicates():
    complete_barcodes = []

    for ballot in valid_ballots():
        forms = distinct_forms(ballot)
        final_forms = ResultForm.forms_in_state(
            FormState.ARCHIVED, pks=[r.pk for r in forms])

        if not SPECIAL_BALLOTS or ballot.number in SPECIAL_BALLOTS:
            complete_barcodes.extend([r.barcode for r in final_forms])

    result_forms = ResultForm.objects\
        .select_related().filter(barcode__in=complete_barcodes)

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


class DashboardView(LoginRequiredMixin,
                    mixins.GroupRequiredMixin,
                    TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/home.html"

    def get(self, *args, **kwargs):
        group_logins = [g.lower().replace(' ', '_') for g in groups.GROUPS]

        return self.render_to_response(self.get_context_data(
            groups=group_logins))


class FormProgressView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_progress.html"

    def get(self, *args, **kwargs):
        form_list = ResultForm.objects.exclude(
            form_state=FormState.UNSUBMITTED)

        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(
            forms=forms))


class FormDuplicatesView(LoginRequiredMixin,
                         mixins.GroupRequiredMixin,
                         TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_duplicates.html"

    def get(self, *args, **kwargs):
        form_list = duplicates()

        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(
            forms=forms))


class FormResultsDuplicatesView(LoginRequiredMixin,
                                mixins.GroupRequiredMixin,
                                TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_results_duplicates.html"

    def get(self, *args, **kwargs):
        form_list = get_results_duplicates()

        forms = paging(form_list, self.request)

        return self.render_to_response(self.get_context_data(forms=forms))


class FormProgressDataView(LoginRequiredMixin,
                           mixins.GroupRequiredMixin,
                           mixins.DatatablesDisplayFieldsMixin,
                           DatatablesView):
    group_required = groups.SUPER_ADMINISTRATOR
    model = ResultForm
    queryset = ResultForm.objects.exclude(form_state=FormState.UNSUBMITTED)
    fields = (
        'barcode',
        'center__code',
        'station_number',
        'ballot__number',
        'center__office__name',
        'center__office__number',
        'ballot__race_type',
        'form_state',
        'rejected_count',
        'modified_date',
    )
    display_fields = (
        ('barcode', 'barcode'),
        ('center__code', 'center_code'),
        ('station_number', 'station_number'),
        ('ballot__number', 'ballot_number'),
        ('center__office__name', 'center_office'),
        ('center__office__number', 'center_office_number'),
        ('ballot__race_type', 'ballot_race_type_name'),
        ('form_state', 'form_state_name'),
        ('rejected_count', 'rejected_count'),
        ('modified_date', 'modified_date_formatted'),
    )


class FormDuplicatesDataView(FormProgressDataView):
    queryset = duplicates()


class FormActionView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.ReverseSuccessURLMixin,
                     TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/form_action.html"
    success_url = 'form-action-view'

    def get(self, *args, **kwargs):
        audits = Audit.objects.filter(
            active=True,
            reviewed_supervisor=True,
            resolution_recommendation=AuditResolution.
            MAKE_AVAILABLE_FOR_ARCHIVE).all()

        return self.render_to_response(self.get_context_data(
            audits=audits))

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = post_data.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        self.request.session['result_form'] = result_form.pk

        if 'review' in post_data:
            return redirect('audit-review')
        elif 'confirm' in post_data:
            result_form.reject()
            result_form.skip_quarantine_checks = True
            result_form.save()

            audit = result_form.audit
            audit.active = False
            audit.save()

            return redirect(self.success_url)
        else:
            raise SuspiciousOperation('Unknown POST response type')


class ResultExportView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/result_export.html"

    def get(self, *args, **kwargs):
        report = kwargs.get('report')
        if report:
            return get_result_export_response(report)
        return super(ResultExportView, self).get(*args, **kwargs)


class RemoveCenterView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       SuccessMessageMixin,
                       FormView):
    form_class = RemoveCenterForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_center.html"
    success_url = 'super-administrator'
    success_message = _(u"Center Successfully Removed.")

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            center = form.save()
            self.success_message = _(
                u"Successfully removed center %(center)s"
                % {'center': center.code})
            return self.form_valid(form)
        return self.form_invalid(form)


class DisableEntityView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        SuccessMessageMixin,
                        FormView):
    form_class = DisableEntityForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/disable_entity.html"
    success_url = 'center-list'

    def get(self, *args, **kwargs):
        stationNumber = kwargs.get('stationNumber')
        centerCode = kwargs.get('centerCode')

        entityName = u'Center' if centerCode else u'Station'

        self.initial = {
            'centerCodeInput': centerCode,
            'stationNumberInput': stationNumber
        }
        self.success_message = _(u"%s Successfully Disabled.") % entityName
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            entity = form.save()

            if isinstance(entity, Center):
                self.success_message = _(
                    u"Successfully disabled center %(center)s"
                    % {'center': entity.code})
            else:
                self.success_message = _(
                    u"Successfully disabled station %(stationNumber)s"
                    % {'stationNumber': entity.station_number})
            return self.form_valid(form)
        return self.form_invalid(form)


class EnableEntityView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       SuccessMessageMixin,
                       TemplateView):
    group_required = groups.SUPER_ADMINISTRATOR
    success_url = 'center-list'

    def get(self, *args, **kwargs):
        stationNumber = kwargs.get('stationNumber')
        centerCode = kwargs.get('centerCode')

        entityName = u'Center' if not stationNumber else u'Station'

        self.success_message = _(u"%s Successfully enabled.") % entityName

        disableEnableEntity(centerCode, stationNumber)

        return redirect(self.success_url)


class RemoveStationView(LoginRequiredMixin,
                        mixins.GroupRequiredMixin,
                        mixins.ReverseSuccessURLMixin,
                        SuccessMessageMixin,
                        FormView):
    form_class = RemoveStationForm
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/remove_station.html"
    success_url = 'super-administrator'
    success_message = _(u"Station Successfully Removed.")

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            station = form.save()
            self.success_message = _(
                u"Successfully removed station %(station)s from "
                u"center %(center)s." % {'center': station.center.code,
                                         'station': station.station_number})
            return self.form_valid(form)
        return self.form_invalid(form)
