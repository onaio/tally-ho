from time import time
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib import auth

from tally_ho.apps.tally.models.site_info import SiteInfo


class IdleTimeout(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_visit = request.session.get('last_visit')
            site_id = getattr(settings, "SITE_ID", None)
            IDLE_TIMEOUT = None

            try:
                siteinfo = SiteInfo.objects.get(site__pk=site_id)
            except SiteInfo.DoesNotExist:
                IDLE_TIMEOUT = getattr(settings, 'DEFAULT_IDLE_TIMEOUT')
            else:
                IDLE_TIMEOUT = siteinfo.user_idle_timeout

            if last_visit:
                time_passed = datetime.now() - datetime.fromtimestamp(
                    last_visit)

                if time_passed > timedelta(0, IDLE_TIMEOUT * 60, 0):
                    auth.logout(request)

            if request.user.is_authenticated:
                # if user is not logged out, set the new last_visit
                request.session['last_visit'] = int(time())

        return self.get_response(request)
