import os
import json
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import translation

from tally_ho.libs.permissions import groups


def debug(request):
    return {"debug": getattr(settings, "DEBUG", False)}


def is_superadmin(request):
    _is_superadmin = False

    if hasattr(request, "user"):
        _is_superadmin = groups.SUPER_ADMINISTRATOR in groups.user_groups(
            request.user
        )

    return {"is_superadmin": _is_superadmin}


def is_tallymanager(request):
    _is_tallymanager = False

    if hasattr(request, "user"):
        _is_tallymanager = groups.TALLY_MANAGER in groups.user_groups(
            request.user
        )

    return {"is_tallymanager": _is_tallymanager}


def locale(request):
    locale = request.session.get('locale') or getattr(
        settings, "LANGUAGE_CODE", None)
    if locale and translation.check_for_language(locale):
        translation.activate(locale)
    return {"locale": locale}


def get_datatables_language_de_from_locale(request):
    language_de = None
    try:
        locale_val = locale(request).get('locale')
        with open(
            os.path.join(
                getattr(settings, "BASE_DIR", None),
                'apps',
                'tally',
                'static',
                'i18n',
                '{}.json'.format(locale_val)
            ),
            'r'
        ) as f:
            language_de = json.load(f)
    except Exception:
        pass
    return language_de


def site_name(request):
    site_name = getattr(settings, "SITE_NAME", None)
    site_id = getattr(settings, "SITE_ID", None)

    if not site_name:
        try:
            site = Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            site_name = "HENC RMS"
        else:
            site_name = site.name

    return {"SITE_NAME": site_name}
