from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import translation


def debug(request):
    return {'debug': getattr(settings, 'DEBUG', False)}


def locale(request):
    return {'locale': translation.get_language_from_request(request)}


def site_name(request):
    site_id = getattr(settings, 'SITE_ID', None)
    try:
        site = Site.objects.get(pk=site_id)
    except Site.DoesNotExist:
        site_name = 'example.org'
    else:
        site_name = site.name
    return {'SITE_NAME': site_name}
