"""Template tags for rendering result form attachments."""

from django import template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from tally_ho.libs.models.enums.result_form_image_source import (
    ResultFormImageSource,
)

register = template.Library()

_SOURCE_LABELS = {
    ResultFormImageSource.PVP_IMPORT: _("from PVP"),
    ResultFormImageSource.UPLOAD: _("uploaded"),
}


@register.inclusion_tag("includes/_result_form_images.html")
def result_form_images(result_form):
    """Render the gallery of images attached to a result form.

    Renders nothing when the form has no images. Each image is
    normalized to a view dict so the template does not reach into the
    model — the image URL is built in one place here, which is also
    where the authenticated media route is wired in.
    """
    images = [
        {
            "url": reverse(
                "result-form-image",
                kwargs={
                    "tally_id": image.tally_id,
                    "image_id": image.id,
                },
            ),
            "kind": image.kind.label,
            "source": _SOURCE_LABELS.get(image.source, image.source.label),
            "caption": image.caption,
            "created_date": image.created_date,
        }
        for image in result_form.images.filter(active=True)
    ]
    return {"images": images}
