from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.utils.importlib import import_module

from mock import patch

from tally_system.libs.middleware.idle_timeout import IdleTimeout


class TestMiddleware(TestCase):

    def setUp(self):
        bob = User.objects.create(username='bob', password='bob')
        self.request = RequestFactory().get('/')
        self.request.user = bob
        self.request.session = self._session()

    def _session(self):
        if 'django.contrib.sessions' in settings.INSTALLED_APPS:
            engine = import_module(settings.SESSION_ENGINE)
            return engine.SessionStore('test')
        return {}

    @patch('tally_system.libs.middleware.idle_timeout.time')
    def test_idle_timeout_last_visit_is_set(self, time_mock):
        idt = IdleTimeout()
        t1 = 1391795951
        time_mock.return_value = t1
        self.assertNotIn('last_visit', self.request.session)
        idt.process_request(self.request)
        self.assertIn('last_visit', self.request.session)
        self.assertEqual(self.request.session['last_visit'], t1)

    @patch('tally_system.libs.middleware.idle_timeout.datetime')
    def test_idle_timeout_user_logged_out(self, datetime_mock):
        idt = IdleTimeout()
        t1 = 1391795951
        t2 = 1391800228
        datetime_mock.now.return_value = datetime.fromtimestamp(t2)
        datetime_mock.fromtimestamp = datetime.fromtimestamp
        settings.IDLE_TIMEOUT = 2  # 2 minutes
        self.request.session['last_visit'] = t1
        idt.process_request(self.request)
        self.assertNotIn('last_visit', self.request.session)
