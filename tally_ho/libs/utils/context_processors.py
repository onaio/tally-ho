from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import translation

from tally_ho.libs.permissions import groups


def debug(request):
    return {'debug': getattr(settings, 'DEBUG', False)}


def is_superadmin(request):
    is_superadmin = False

    if getattr(request, 'user'):
        is_superadmin = groups.SUPER_ADMINISTRATOR in groups.user_groups(
            request.user)

    return {'is_superadmin': is_superadmin}


def is_tallymanager(request):
    is_tallymanager = False

    if getattr(request, 'user'):
        is_tallymanager = groups.TALLY_MANAGER in groups.user_groups(
            request.user)

    return {'is_tallymanager': is_tallymanager}


def locale(request):
    return {'locale': translation.get_language_from_request(request)}


def site_name(request):
    site_name = getattr(settings, 'SITE_NAME', None)
    site_id = getattr(settings, 'SITE_ID', None)

    if not site_name:
        try:
            site = Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            site_name = 'HENC RMS'
        else:
            site_name = site.name

    return {'SITE_NAME': site_name}
