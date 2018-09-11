from time import time
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib import auth


class IdleTimeout(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_visit = request.session.get('last_visit')

            if last_visit:
                IDLE_TIMEOUT = getattr(settings, 'IDLE_TIMEOUT', 60)
                time_passed = datetime.now() - datetime.fromtimestamp(
                    last_visit)

                if time_passed > timedelta(0, IDLE_TIMEOUT * 60, 0):
                    auth.logout(request)

            if request.user.is_authenticated:
                # if user is not logged out, set the new last_visit
                request.session['last_visit'] = int(time())

        return self.get_response(request)
