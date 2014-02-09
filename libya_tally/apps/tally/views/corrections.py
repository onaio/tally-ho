from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.forms import ValidationError
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView
from guardian.mixins import LoginRequiredMixin

from libya_tally.apps.tally.forms.barcode_form import\
    BarcodeForm
from libya_tally.apps.tally.forms.pass_to_quality_control_form import\
    PassToQualityControlForm
from libya_tally.apps.tally.forms.recon_form import ReconForm
from libya_tally.apps.tally.models.reconciliation_form import\
    ReconciliationForm
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.permissions import groups
from libya_tally.libs.views.session import session_matches_post_result_form
from libya_tally.libs.views import mixins
from libya_tally.libs.views.corrections import get_matched_forms,\
    get_results_for_race_type, save_final_results, save_general_results,\
    save_women_results
from libya_tally.libs.views.form_state import form_in_state, safe_form_in_state


def incorrect_checks(post_data, result_form, success_url):
    if 'reject_submit' in post_data:
        result_form.reject()
    else:
        raise SuspiciousOperation('Unknown POST response type')

    return redirect(success_url)


def get_recon_form(result_form):
    results = result_form.reconciliationform_set.filter(active=True)

    if results.count() != 2:
        raise SuspiciousOperation(_(u"There should be exactly two "
                                    u"reconciliation results."))

    reconciliation_form_1 = recon_form_for_version(
        results, EntryVersion.DATA_ENTRY_1)
    reconciliation_form_2 = recon_form_for_version(
        results, EntryVersion.DATA_ENTRY_2)

    recon = []
    for field in reconciliation_form_1:
        recon.append((field, reconciliation_form_2[field.name]))

    return recon


def match_forms(result_form):
    matches, no_match = get_matched_forms(result_form)
    return len(no_match) == 0


def recon_form_for_version(results, entry_version):
    return ReconForm(data=model_to_dict(
        results.filter(entry_version=entry_version)[0]))


def save_recon(post_data, user, result_form):
        recon_forms = result_form.reconciliationform_set
        recon_form1 = recon_form_for_version(
            recon_forms, EntryVersion.DATA_ENTRY_1)

        recon_form_corrections = ReconForm(post_data)

        corrections = {f.name: f.value() for f in recon_form_corrections
                       if f.value() is not None}

        updated = {f.name: f.value() for f in recon_form1}
        updated.update(corrections)

        recon_form_final = ReconciliationForm(**updated)
        recon_form_final.user = user
        recon_form_final.result_form = result_form
        recon_form_final.entry_version = EntryVersion.FINAL
        recon_form_final.save()


class CorrectionView(LoginRequiredMixin,
                     mixins.GroupRequiredMixin,
                     mixins.ReverseSuccessURLMixin,
                     FormView):
    form_class = BarcodeForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "tally/barcode_verify.html"
    success_url = 'corrections-match'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_('Correction')))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            form = safe_form_in_state(result_form, FormState.CORRECTION,
                                      form)

            if form:
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk

            if result_form.corrections_passed:
                return redirect(self.success_url)
            else:
                return redirect('corrections-required')
        else:
            return self.form_invalid(form)


class CorrectionMatchView(LoginRequiredMixin,
                          mixins.GroupRequiredMixin,
                          mixins.ReverseSuccessURLMixin,
                          FormView):
    form_class = PassToQualityControlForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "tally/corrections/match.html"
    success_url = 'corrections-clerk'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])

        return self.render_to_response(
            self.get_context_data(result_form=result_form))

    @transaction.atomic
    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            pk = session_matches_post_result_form(
                form.cleaned_data, self.request)
            result_form = get_object_or_404(ResultForm, pk=pk)
            form_in_state(result_form, [FormState.CORRECTION])

            if not match_forms(result_form):
                raise Exception(_(u"Results do not match."))

            save_final_results(result_form, self.request.user)

            result_form.form_state = FormState.QUALITY_CONTROL
            result_form.save()

            del self.request.session['result_form']

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CorrectionRequiredView(LoginRequiredMixin,
                             mixins.GroupRequiredMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    form_class = PassToQualityControlForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "tally/corrections/required.html"
    success_url = 'corrections-clerk'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])

        recon = get_recon_form(result_form)
        results_general = get_results_for_race_type(result_form,
                                                    RaceType.GENERAL)
        results_women = get_results_for_race_type(result_form,
                                                  RaceType.WOMEN)
        errors = self.request.session.get('errors')

        if errors:
            del self.request.session['errors']

        return self.render_to_response(
            self.get_context_data(errors=errors,
                                  result_form=result_form,
                                  reconciliation_form=recon,
                                  candidates_general=results_general,
                                  candidates_women=results_women))

    @transaction.atomic
    def post(self, race_type):
        post_data = self.request.POST
        pk = session_matches_post_result_form(post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])

        if 'submit_corrections' in post_data:
            user = self.request.user

            try:
                save_general_results(result_form, post_data, user)
                save_women_results(result_form, post_data, user)
            except ValidationError as e:
                self.request.session['errors'] = e.message
                return redirect('corrections-required')

            if result_form.reconciliationform_set.all():
                save_recon(post_data, user, result_form)

            result_form.form_state = FormState.QUALITY_CONTROL
            result_form.save()

            return redirect(self.success_url)
        else:
            return incorrect_checks(post_data, result_form,
                                    'corrections-clerk')
