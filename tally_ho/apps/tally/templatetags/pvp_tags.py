"""Template tags for PVP-sourced ResultForm tagging."""

from django import template

register = template.Library()


@register.inclusion_tag("includes/_pvp_badge.html")
def pvp_badge(result_form):
    """Render a small "PVP" badge + caption when a result form was
    populated from a PVP upload. Renders nothing otherwise.
    """
    return {"result_form": result_form}
