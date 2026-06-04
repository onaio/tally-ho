"""Super-admin views for the PVP bundle upload flow.

Three-step user journey:

1. Upload (FormView): POST a .zip → bundle row created with status=PENDING,
   zip persisted via `PvpUploadBundle.zip_file`. Redirects to confirm.
2. Confirm (TemplateView): re-parses the bundle, runs row-level validation,
   shows "will import" / "will skip" / "missing images" lists. POST enqueues
   the celery import task and redirects to result.
3. Result (TemplateView): shows current bundle status / counts. The celery
   task flips status PENDING → IMPORTING → COMPLETED (or FAILED).
"""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView, View
from guardian.mixins import LoginRequiredMixin

from tally_ho.apps.tally.forms.pvp_upload_form import PvpUploadForm
from tally_ho.apps.tally.management.commands.async_pvp_import import (
    async_pvp_import,
)
from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups
from tally_ho.libs.pvp.bundle import (
    InvalidBundleError, DuplicateBarcodeError, parse_bundle,
)
from tally_ho.libs.pvp.validation import validate_row
from tally_ho.libs.views.mixins import GroupRequiredMixin, TallyAccessMixin


class PvpUploadView(
    LoginRequiredMixin, GroupRequiredMixin, TallyAccessMixin, FormView,
):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/pvp_upload.html"
    form_class = PvpUploadForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tally_id"] = self.kwargs["tally_id"]
        return context

    def form_valid(self, form):
        tally_id = self.kwargs["tally_id"]
        tally = get_object_or_404(Tally, id=tally_id)
        upload = form.cleaned_data["zip_file"]

        # request.user is a Django User; the FK targets UserProfile (the
        # multi-table-inherited subclass). Fetch the matching profile.
        uploaded_by = UserProfile.objects.get(id=self.request.user.id)

        # Two-step save: persist row to get id, then attach zip and re-save.
        bundle = PvpUploadBundle.objects.create(
            tally=tally,
            uploaded_by=uploaded_by,
            filename=upload.name,
        )
        bundle.zip_file = upload
        bundle.save()

        # Sanity-parse the zip up front so the user gets immediate feedback
        # if the bundle is structurally broken. The confirm view re-parses
        # for display.
        try:
            parse_bundle(bundle.zip_file.path)
        except (InvalidBundleError, DuplicateBarcodeError) as exc:
            bundle.delete()  # zip_file deletion handled by FileField
            form.add_error("zip_file", str(exc))
            return self.form_invalid(form)

        return redirect(
            "pvp-confirm", tally_id=tally_id, bundle_id=bundle.id,
        )


class PvpConfirmView(
    LoginRequiredMixin, GroupRequiredMixin, TallyAccessMixin, TemplateView,
):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/pvp_confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tally_id = self.kwargs["tally_id"]
        bundle_id = self.kwargs["bundle_id"]
        bundle = get_object_or_404(
            PvpUploadBundle, id=bundle_id, tally_id=tally_id,
        )
        parsed = parse_bundle(bundle.zip_file.path)

        barcodes = [s.barcode for s in parsed.rows]
        rf_by_barcode = {
            rf.barcode: rf
            for rf in ResultForm.objects.filter(
                tally=bundle.tally, barcode__in=barcodes,
            )
        }
        will_import, will_skip = [], []
        for sub in parsed.rows:
            result = validate_row(sub, bundle.tally, rf_by_barcode)
            if result.valid:
                will_import.append(sub)
            else:
                will_skip.append((sub, result.reason))

        context.update({
            "tally_id": tally_id,
            "bundle": bundle,
            "will_import": will_import,
            "will_skip": will_skip,
            "missing_images": parsed.missing_images,
        })
        return context

    def post(self, request, *args, **kwargs):
        tally_id = self.kwargs["tally_id"]
        bundle_id = self.kwargs["bundle_id"]
        bundle = get_object_or_404(
            PvpUploadBundle, id=bundle_id, tally_id=tally_id,
        )
        async_pvp_import.delay(
            bundle_id=bundle.id, user_id=request.user.id,
        )
        messages.success(
            request, _("PVP import enqueued."),
        )
        return redirect(
            "pvp-result", tally_id=tally_id, bundle_id=bundle.id,
        )


class PvpResultView(
    LoginRequiredMixin, GroupRequiredMixin, TallyAccessMixin, TemplateView,
):
    group_required = groups.SUPER_ADMINISTRATOR
    template_name = "super_admin/pvp_result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tally_id = self.kwargs["tally_id"]
        bundle_id = self.kwargs["bundle_id"]
        bundle = get_object_or_404(
            PvpUploadBundle, id=bundle_id, tally_id=tally_id,
        )
        context.update({
            "tally_id": tally_id,
            "bundle": bundle,
        })
        return context


class PvpStatusView(
    LoginRequiredMixin, GroupRequiredMixin, TallyAccessMixin, View,
):
    group_required = groups.SUPER_ADMINISTRATOR

    def get(self, request, tally_id, bundle_id):
        bundle = get_object_or_404(
            PvpUploadBundle, id=bundle_id, tally_id=tally_id,
        )
        return JsonResponse({
            "status": bundle.status.name,
            "number_of_submissions": bundle.number_of_submissions,
            "imported_at": (
                bundle.imported_at.isoformat()
                if bundle.imported_at else None
            ),
        })
