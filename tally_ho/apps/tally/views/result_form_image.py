from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import View

from tally_ho.apps.tally.models.result_form_image import ResultFormImage
from tally_ho.libs.utils.image_validation import IMAGE_CONTENT_TYPES
from tally_ho.libs.views.mixins import TallyAccessMixin


class ResultFormImageView(LoginRequiredMixin, TallyAccessMixin, View):
    """Stream a result form image to users with access to its tally.

    Guards the sensitive form photographs behind login + tally-access
    checks rather than the open ``^media/`` route. The response declares
    an explicit image content type and ``X-Content-Type-Options: nosniff``
    so a browser can never be tricked into interpreting a stored file as
    anything other than the image it was verified to be at ingest.
    """

    def get(self, request, tally_id, image_id, *args, **kwargs):
        # Only serve active images, so a direct URL agrees with the
        # gallery and exports (both filter active=True). A soft-deleted
        # image — e.g. deactivated by a form reset — 404s rather than
        # staying fetchable.
        image = get_object_or_404(
            ResultFormImage, id=image_id, tally_id=tally_id, active=True,
        )
        content_type = IMAGE_CONTENT_TYPES.get(
            image.image_format, "application/octet-stream",
        )
        try:
            response = FileResponse(
                image.image.open("rb"), content_type=content_type,
            )
        except FileNotFoundError:
            raise Http404
        response["X-Content-Type-Options"] = "nosniff"
        return response
