import dateutil.parser
from django.core.serializers.json import json, DjangoJSONEncoder
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.forms import ValidationError
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views.generic import FormView, TemplateView
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.barcode_form import\
    BarcodeForm
from tally_ho.apps.tally.forms.pass_to_quality_control_form import\
    PassToQualityControlForm
from tally_ho.apps.tally.forms.recon_form import ReconForm
from tally_ho.apps.tally.models.reconciliation_form import\
    ReconciliationForm
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.views.session import session_matches_post_result_form
from tally_ho.libs.views import mixins
from tally_ho.libs.views.corrections import get_matched_forms,\
    result_form_candidate_results,\
    save_final_results, save_form_results,\
    update_result_form_entries_with_de_errors
from tally_ho.libs.views.form_state import form_in_state,\
    safe_form_in_state


def save_result_form_processing_stats(
    request,
    encoded_start_time,
    result_form
):
    """Save result form processing stats.

    :param request: The request object.
    :param encoded_start_time: The encoded time the result form started
        to be processed.
    :param result_form: The result form being processed by the corrections
        clerk.
    """
    corrections_start_time = dateutil.parser.parse(
        encoded_start_time)
    del request.session['encoded_result_form_corrections_start_time']

    corrections_end_time = timezone.now()
    form_processing_time_in_seconds =\
        (corrections_end_time - corrections_start_time).total_seconds()

    ResultFormStats.objects.get_or_create(
        processing_time=form_processing_time_in_seconds,
        user=request.user.userprofile,
        result_form=result_form)


def get_recon_form_dict(result_form):
    recon_forms = result_form.reconciliationform_set.filter(active=True)
    recon_form1 = recon_form_for_version(
        recon_forms, EntryVersion.DATA_ENTRY_1)

    return {f.name: f.value() for f in recon_form1}


def save_final_recon_form(updated, user, result_form):
    """Set and save values in a final reconciliation form.

    :param updated: A key value dict of values for the reconciliation form.
    :param user: The user to associate with the reconciliation form.
    :param result_form: The result form to associate with this reconciliation
        form.
    """
    recon_form_final = ReconciliationForm(**updated)
    recon_form_final.user = user.userprofile
    recon_form_final.result_form = result_form
    recon_form_final.entry_version = EntryVersion.FINAL
    recon_form_final.save()


def incorrect_checks(post_data, result_form, success_url, tally_id=None):
    """Perform non-success operations on a result form give the post data.

    :param post_data: Data to determine the appropriate action for.
    :param result_form: Result form to reject if a rejection.
    :param success_url: Url to redirect to.

    :raises: `SuspiciousOperation` if the post data is an unexpected value.
    :returns: A redirect to the success url.
    """
    if 'reject_submit' in post_data:
        result_form.reject()
    elif 'abort_submit' in post_data:
        pass
    else:
        raise SuspiciousOperation('Unknown POST response type')

    return redirect(success_url, tally_id=tally_id)


def get_corrections_forms(result_form):
    """Return a list of corrections forms for the reconciliation and each
    result type.

    :param result_form: The result form to fetch results for.

    :returns: A list of corrections forms.
    """
    recon = get_recon_form(result_form) if result_form.has_recon else None
    candidate_results =\
        result_form_candidate_results(result_form, num_results=2)

    return [recon, candidate_results]


def get_recon_form(result_form):
    """Build a list of reconciliation form data from the two data entry
    versions.

    :param result_form: The result form to get reconciliation forms from.

    :returns: A list of tuples of the field from data entry 1, data entry 2,
        and the name of the field.
    """
    results = result_form.corrections_reconciliationforms

    if results.count() != 2:
        final_results = results.filter(entry_version=EntryVersion.FINAL)

        if results.count() - final_results.count() == 2:
            # final results exist, deactivate them and continue
            for final in final_results:
                final.active = False
                final.save()
        else:
            raise SuspiciousOperation(_(u"There should be exactly two "
                                        u"reconciliation results."))

    recon_form_1 = recon_form_for_version(results, EntryVersion.DATA_ENTRY_1)
    recon_form_2 = recon_form_for_version(results, EntryVersion.DATA_ENTRY_2)

    return [(field, recon_form_2[field.name], field.data.__class__.__name__)
            for field in recon_form_1]


def match_forms(result_form):
    matches, no_match = get_matched_forms(result_form)
    return len(no_match) == 0


def recon_form_for_version(results, entry_version):
    return ReconForm(data=model_to_dict(results.filter(
        entry_version=entry_version)[0]))


def save_unchanged_final_recon_form(result_form, user):
    if result_form.reconciliationform_exists:
        updated = get_recon_form_dict(result_form)
        save_final_recon_form(updated, user, result_form)


def save_recon(post_data, user, result_form):
    """Build final reconciliation form from existing and submitted data.

    :param post_data: The form data to retrieve corrections from.
    :param user: The user to associate with the final reconciliation form.
    :param result_form: The result form to update reconciliation forms for.
    """
    corrections = {}
    mismatched = 0
    data_entry_1_errors = 0
    data_entry_2_errors = 0

    for v1, v2, _type in get_recon_form(result_form):
        if v1.data != v2.data:
            mismatched += 1
            value = post_data.get(v1.name)
            if value:
                if value == 'False':
                    value = False
                corrections[v1.name] = value

            # Error occured at data entry 1 stage
            if int(value) != v1.data:
                data_entry_1_errors += 1

            # Error occured at data entry 2 stage
            if int(value) != v2.data:
                data_entry_2_errors += 1

    if len(corrections) < mismatched:
        raise ValidationError(
            _('Please select correct results for all mis-matched votes.'))

    updated = get_recon_form_dict(result_form)
    updated = {k: v for k, v in updated.items() if k not in corrections}
    updated.update(corrections)

    save_final_recon_form(updated, user, result_form)

    if data_entry_1_errors or data_entry_2_errors:
        update_result_form_entries_with_de_errors(
            data_entry_1_errors, data_entry_2_errors, post_data['tally_id'])


class CorrectionView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.TallyAccessMixin,
                     mixins.ReverseSuccessURLMixin,
                     FormView):
    form_class = BarcodeForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "barcode_verify.html"
    success_url = 'corrections-match'

    def get_context_data(self, **kwargs):
        tally_id = self.kwargs.get('tally_id')

        context = super(CorrectionView, self).get_context_data(**kwargs)
        context['tally_id'] = tally_id
        context['form_action'] = ''
        context['header_text'] = _('Corrections')
        self.request.session[
            'encoded_result_form_corrections_start_time'] =\
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))

        return context

    def get_initial(self):
        initial = super(CorrectionView, self).get_initial()
        initial['tally_id'] = self.kwargs.get('tally_id')

        return initial

    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode'] or\
                form.cleaned_data['barcode_scan']
            result_form = get_object_or_404(ResultForm,
                                            barcode=barcode,
                                            tally__id=tally_id)
            form = safe_form_in_state(result_form, FormState.CORRECTION, form)

            if form:
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk

            if result_form.corrections_passed:
                return redirect(self.success_url, tally_id=tally_id)
            else:
                return redirect('corrections-required', tally_id=tally_id)
        else:
            return self.form_invalid(form)


class CorrectionMatchView(LoginRequiredMixin,
                          mixins.GroupRequiredMixin,
                          mixins.TallyAccessMixin,
                          mixins.ReverseSuccessURLMixin,
                          FormView):
    form_class = PassToQualityControlForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "corrections/match.html"
    success_url = 'corrections'

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, [FormState.CORRECTION])

        return self.render_to_response(
            self.get_context_data(result_form=result_form, tally_id=tally_id))

    @transaction.atomic
    def post(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            pk = session_matches_post_result_form(
                form.cleaned_data, self.request)
            result_form = get_object_or_404(ResultForm,
                                            pk=pk,
                                            tally__id=tally_id)
            form_in_state(result_form, [FormState.CORRECTION])

            if not result_form.corrections_passed:
                raise Exception(_(u"Results do not match."))

            save_final_results(result_form, self.request.user)
            save_unchanged_final_recon_form(result_form, self.request.user)

            result_form.form_state = FormState.QUALITY_CONTROL
            result_form.save()

            encoded_start_time = self.request.session.get(
                'encoded_result_form_corrections_start_time')
            # Track corrections clerks result form processing time
            save_result_form_processing_stats(
                self.request, encoded_start_time, result_form)

            del self.request.session['result_form']

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return self.form_invalid(form)


class CorrectionRequiredView(LoginRequiredMixin,
                             mixins.GroupRequiredMixin,
                             mixins.TallyAccessMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    form_class = PassToQualityControlForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "corrections/required.html"
    success_url = 'corrections-success'
    failed_url = 'suspicious-error'

    def corrections_response(self, result_form, errors=None):
        tally_id = self.kwargs.get('tally_id')
        recon, candidate_results =\
            get_corrections_forms(result_form)
        election_level = result_form.ballot.electrol_race.election_level

        return self.render_to_response(
            self.get_context_data(errors=errors,
                                  result_form=result_form,
                                  reconciliation_form=recon,
                                  candidate_results=candidate_results,
                                  header=election_level,
                                  prefix=election_level.lower(),
                                  tally_id=tally_id))

    def get(self, *args, **kwargs):
        tally_id = self.kwargs['tally_id']
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, [FormState.CORRECTION])

        return self.corrections_response(result_form)

    def post(self, *args, **kwargs):
        tally_id = self.kwargs['tally_id']
        post_data = self.request.POST
        post_data = post_data.copy()
        post_data['tally_id'] = tally_id
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        form_in_state(result_form, FormState.CORRECTION)

        if 'submit_corrections' in post_data:
            user = self.request.user

            try:
                with transaction.atomic():
                    if result_form.reconciliationform_exists:
                        save_recon(post_data, user, result_form)
                    save_form_results(result_form, post_data, user)
            except ValidationError as e:
                return self.corrections_response(result_form, u"%s" % e)
            except SuspiciousOperation as e:
                self.request.session['error_message'] = u"%s" % e

                if result_form.form_state == FormState.DATA_ENTRY_1:
                    result_form.save()

                return redirect(self.failed_url, tally_id=tally_id)
            else:
                result_form.form_state = FormState.QUALITY_CONTROL
                result_form.save()

            return redirect(self.success_url, tally_id=tally_id)
        else:
            return incorrect_checks(post_data,
                                    result_form,
                                    'corrections',
                                    tally_id)


class ConfirmationView(LoginRequiredMixin,
                       mixins.GroupRequiredMixin,
                       mixins.TallyAccessMixin,
                       TemplateView):
    template_name = "success.html"
    group_required = groups.CORRECTIONS_CLERK

    def get(self, *args, **kwargs):
        tally_id = kwargs.get('tally_id')
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk, tally__id=tally_id)
        del self.request.session['result_form']

        encoded_start_time = self.request.session.get(
            'encoded_result_form_corrections_start_time')
        # Track corrections clerks result form processing time
        save_result_form_processing_stats(
            self.request, encoded_start_time, result_form)

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  header_text=_('Corrections'),
                                  next_step=_('Quality Control & Archiving'),
                                  start_url='corrections',
                                  tally_id=tally_id))
