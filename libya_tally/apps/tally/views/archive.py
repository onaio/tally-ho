from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.generic import FormView

from libya_tally.apps.tally.forms.barcode_form import\
    BarcodeForm
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.utils.common import session_matches_post_result_form
from libya_tally.libs.views import mixins
from libya_tally.libs.views.form_state import form_in_state, safe_form_in_state


def match_forms(result_form):
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

    return len(matches) == results_v1.count()


class ArchiveView(mixins.GroupRequiredMixin,
                  mixins.ReverseSuccessURLMixin,
                  FormView):
    form_class = BarcodeForm
    group_required = groups.ARCHIVE_CLERK
    template_name = "tally/barcode_verify.html"
    success_url = 'archive-print'

    def get(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        return self.render_to_response(
            self.get_context_data(form=form, header_text=_('Archiving')))

    def post(self, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            result_form = get_object_or_404(ResultForm, barcode=barcode)

            form = safe_form_in_state(result_form, FormState.ARCHIVING,
                                      form)

            if form:
                return self.form_invalid(form)

            self.request.session['result_form'] = result_form.pk

            return redirect('archive-print')
        else:
            return self.form_invalid(form)


class ArchivePrintView(mixins.GroupRequiredMixin,
                       mixins.ReverseSuccessURLMixin,
                       FormView):
    group_required = groups.ARCHIVE_CLERK
    template_name = "tally/archive/print_cover.html"
    success_url = 'archive-clerk'

    def get(self, *args, **kwargs):
        pk = self.request.session.get('result_form')
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.ARCHIVING)

        if result_form.audit:
            cover_type = _('Quarantined')
            form_state = _('QUARANTINED FORM')
        else:
            cover_type = _('Successful Archive')
            form_state = _('ARCHIVED FORM')

        return self.render_to_response(
            self.get_context_data(result_form=result_form,
                                  cover_type=cover_type,
                                  form_state=form_state))

    @transaction.atomic
    def post(self, *args, **kwargs):
        post_data = self.request.POST
        pk = session_matches_post_result_form(
            post_data, self.request)
        result_form = get_object_or_404(ResultForm, pk=pk)
        form_in_state(result_form, FormState.ARCHIVING)

        result_form.form_state = FormState.ARCHIVED
        result_form.save()

        del self.request.session['result_form']

        return redirect(self.success_url)
