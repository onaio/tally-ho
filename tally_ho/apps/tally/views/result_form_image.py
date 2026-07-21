from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import View

from tally_ho.apps.tally.models.result_form_image import ResultFormImage
from tally_ho.libs.views.mixins import TallyAccessMixin


class ResultFormImageView(LoginRequiredMixin, TallyAccessMixin, View):
    """Stream a result form image to users with access to its tally.

    Guards the sensitive form photographs behind login + tally-access
    checks rather than the open ``^media/`` route.
    """

    def get(self, request, tally_id, image_id, *args, **kwargs):
        image = get_object_or_404(
            ResultFormImage, id=image_id, tally_id=tally_id,
        )
        try:
            return FileResponse(image.image.open("rb"))
        except FileNotFoundError:
            raise Http404
