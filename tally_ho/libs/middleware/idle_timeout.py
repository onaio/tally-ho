from time import time
from datetime import datetime, timedelta
from django.conf import settings

from tally_ho.apps.tally.views.profile import session_expiry_logout_view
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
                idle_timeout_in_seconds = IDLE_TIMEOUT * 60
                days = 0
                microseconds = 0

                if time_passed > timedelta(
                    days, idle_timeout_in_seconds, microseconds
                ):
                    session_expiry_logout_view(request)

            if request.user.is_authenticated:
                # if user is not logged out, set the new last_visit
                request.session['last_visit'] = int(time())

        return self.get_response(request)
