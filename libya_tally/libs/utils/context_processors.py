from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import translation

from libya_tally.libs.permissions import groups


def debug(request):
    return {'debug': getattr(settings, 'DEBUG', False)}


def is_superadmin(request):
    is_superadmin = False

    if getattr(request, 'user'):
        is_superadmin = groups.SUPER_ADMINISTRATOR in groups.user_groups(
            request.user)

    return {'is_superadmin': is_superadmin}


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
