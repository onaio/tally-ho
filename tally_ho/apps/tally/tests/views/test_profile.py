from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.serializers.json import json, DjangoJSONEncoder
from django.utils import timezone

from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.apps.tally.views import profile as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    create_tally,
    create_result_form,
    TestBase,
)


class TestProfile(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_1_CLERK)

    def test_login_view(self):
        request = self.factory.get('/login')
        request.user = self.user
        request.session = {}

        response = views.login(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Signed in as {self.user.username}')
        self.assertContains(
            response, '<a id="logout_link" href="/accounts/logout/">')

    def test_session_expiry_logout_view_during_de_1(self):
        encoded_result_form_data_entry_start_time =\
            json.loads(json.dumps(timezone.now(), cls=DjangoJSONEncoder))
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.DATA_ENTRY_1,
                                         tally=tally)
        data_entry_url = 'enter-results/%s/' % tally.pk
        request = self.factory.post(data_entry_url)
        request.user = self.user
        # Adding session
        middleware = SessionMiddleware(HttpResponse)
        middleware.process_request(request)
        request.session.save()
        request.session['encoded_result_form_data_entry_start_time'] =\
            encoded_result_form_data_entry_start_time
        request.session['result_form'] =\
            result_form.pk
        # Mark request as not requiring CSRF check
        request._dont_enforce_csrf_checks = True

        response = views.session_expiry_logout_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            request.session['encoded_result_form_data_entry_start_time'],
            encoded_result_form_data_entry_start_time)
        self.assertEqual(
            request.session['result_form'],
            result_form.pk)
