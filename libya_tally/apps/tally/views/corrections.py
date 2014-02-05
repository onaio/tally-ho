from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView

from libya_tally.apps.tally.forms.barcode_form import\
    BarcodeForm
from libya_tally.apps.tally.forms.pass_to_quality_control_form import \
    PassToQualityControlForm
from libya_tally.apps.tally.forms.reconciliation_form import ReconciliationForm
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.candidate import Candidate
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.permissions import groups
from libya_tally.libs.utils.common import session_matches_post_result_form, \
    get_matched_results
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state, safe_form_in_state


def get_matched_forms(result_form):
    results_v1 = Result.objects.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_1)\
        .values('candidate', 'votes')
    results_v2 = Result.objects.filter(
        result_form=result_form, entry_version=EntryVersion.DATA_ENTRY_2)\
        .values('candidate', 'votes')

    if not results_v1 or not results_v2:
        raise Exception(_(u"Result Form has no double entries."))

    if results_v1.count() != results_v2.count():
        return False

    tuple_list = [i.items() for i in results_v1]
    matches = [rec for rec in results_v2 if rec.items() in tuple_list]
    no_match = [rec for rec in results_v2 if rec.items() not in tuple_list]

    return matches, no_match


def match_forms(result_form):
    matches, no_match = get_matched_forms(result_form)
    return len(no_match) == 0


class CorrectionView(mixins.GroupRequiredMixin,
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
            return redirect('corrections-dashboard')
        else:
            return self.form_invalid(form)


class CorrectionMatchView(mixins.GroupRequiredMixin,
                          mixins.ReverseSuccessURLMixin,
                          FormView):
    form_class = PassToQualityControlForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "tally/corrections/match.html"
    success_url = 'corrections-dashboard'

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

            results = Result.objects.filter(
                result_form=result_form,
                entry_version=EntryVersion.DATA_ENTRY_2)
            for result in results:
                Result.objects.create(
                    candidate=result.candidate,
                    result_form=result_form,
                    entry_version=EntryVersion.FINAL,
                    votes=result.votes)

            result_form.form_state = FormState.QUALITY_CONTROL
            result_form.save()

            del self.request.session['result_form']

            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class CorrectionDashboardView(mixins.GroupRequiredMixin,
                              mixins.ReverseSuccessURLMixin,
                              FormView):
    form_class = PassToQualityControlForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "tally/corrections/dashboard.html"
    success_url = 'corrections-clerk'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])

        return self.render_to_response(
            self.get_context_data(result_form=result_form))


class AbstractCorrectionView(mixins.GroupRequiredMixin,
                             mixins.ReverseSuccessURLMixin,
                             FormView):
    form_class = PassToQualityControlForm
    group_required = groups.CORRECTIONS_CLERK
    template_name = "tally/corrections/required.html"
    success_url = 'corrections-dashboard'

    def get_candidates(self, result_form, results=None):
        candidates = {}
        if results is None:
            results = result_form.results
        for result in results.order_by('candidate__order',
                                       'entry_version'):
            if result.candidate in candidates.keys():
                candidates[result.candidate].append(result)
            else:
                candidates.update({
                    result.candidate: [result]})
        return candidates

    def get_action(self, header_text, race_type):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])

        results = result_form.results.filter(candidate__race_type=race_type)
        candidates = self.get_candidates(result_form, results)

        results = []
        for c, r in candidates.iteritems():
            results.append((c, r[0], r[1]))
        return self.render_to_response(
            self.get_context_data(header_text=header_text,
                                  result_form=result_form,
                                  candidates=results))

        results = []
        for c, r in candidates.iteritems():
            results.append((c, r[0], r[1]))
        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  candidates=results))

    @transaction.atomic
    def post_action(self, race_type):
        pk = session_matches_post_result_form(self.request.POST, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])
        candidate_fields = [
            f for f in self.request.POST if f.startswith('candidate_')]

        results = result_form.results.filter(candidate__race_type=race_type)
        matches, no_match = get_matched_results(result_form, results)

        if 'submit_corrections' in self.request.POST:
            if len(candidate_fields) != len(no_match):
                raise Exception(
                    _(u"Please select correct results for all"
                      u" mis-matched votes."))

            changed_candidates = []

            for field in candidate_fields:
                candidate_pk = field.replace('candidate_', '')
                candidate = Candidate.objects.get(pk=candidate_pk)
                votes = self.request.POST[field]
                Result.objects.create(
                    candidate=candidate,
                    result_form=result_form,
                    entry_version=EntryVersion.FINAL,
                    votes=votes,
                    user=self.request.user
                )
                changed_candidates.append(candidate)

            results_v2 = results.filter(
                result_form=result_form,
                entry_version=EntryVersion.DATA_ENTRY_2)
            for result in results_v2:
                if result.candidate not in changed_candidates:
                    Result.objects.create(
                        candidate=result.candidate,
                        result_form=result_form,
                        entry_version=EntryVersion.FINAL,
                        votes=result.votes,
                        user=self.request.user
                    )

            return redirect(self.success_url)
        elif 'reject_submit' in self.request.POST:
            result_form.reject()

            return redirect(self.success_url)
        else:
            return redirect(self.success_url)


class CorrectionGeneralView(AbstractCorrectionView):

    def get(self, *args, **kwargs):
        return self.get_action(_(u"General"), RaceType.GENERAL)

    @transaction.atomic
    def post(self, *args, **kwargs):
        return self.post_action(RaceType.GENERAL)


class CorrectionWomenView(AbstractCorrectionView):

    def get(self, *args, **kwargs):
        return self.get_action(_(u"General"), RaceType.WOMEN)

    @transaction.atomic
    def post(self, *args, **kwargs):
        return self.post_action(RaceType.WOMEN)


class CorrectionReconciliationView(AbstractCorrectionView):

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])
        results = result_form.reconciliationform_set.filter(active=True)

        if results.count() < 2:
            raise SuspiciousOperation(_(u"There should be atleast two "
                                        u"reconciliation results."))
        reconciliation_form_1 = ReconciliationForm(data=model_to_dict(
            results.filter(entry_version=EntryVersion.DATA_ENTRY_1)[0]))
        reconciliation_form_2 = ReconciliationForm(data=model_to_dict(
            results.filter(entry_version=EntryVersion.DATA_ENTRY_2)[0]))

        recon = []
        for field in reconciliation_form_1:
            recon.append((field, reconciliation_form_2[field.name]))

        return self.render_to_response(self.get_context_data(
            result_form=result_form,
            header_text=_(u"Reconciliation"),
            reconciliation_form=recon
        ))

    @transaction.atomic
    def post_action(self, race_type):
        pk = session_matches_post_result_form(self.request.POST, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, [FormState.CORRECTION])
        # TODO complete this
