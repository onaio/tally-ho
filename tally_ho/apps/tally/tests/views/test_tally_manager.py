from django.conf import settings
from django.test import RequestFactory

from django.contrib.sites.models import Site
from tally_ho.apps.tally.models.site_info import SiteInfo
from tally_ho.apps.tally.views import tally_manager as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    create_tally,
    TestBase,
)


class TestTallyManager(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

    def test_set_user_timout_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.SetUserTimeOutView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        site_id = getattr(settings, "SITE_ID", None)

        try:
            Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            site = Site.objects.create(name="HENC RMS")
            site_id = site.id

        response = view(
            request,
            site_id=site_id)

        self.assertContains(response, '<h1>Set User Timeout</h1>')
        self.assertContains(
            response,
            '<div class="form-instructions">Set timeout in minutes.</div>')

        user_idle_timeout = None
        try:
            siteinfo = SiteInfo.objects.get(site__pk=site_id)
            user_idle_timeout = siteinfo.user_idle_timeout
        except SiteInfo.DoesNotExist:
            user_idle_timeout = getattr(settings, 'IDLE_TIMEOUT', 60)

        self.assertIn(
            str('Current User Idle Timeout '
                '{} minutes').format(user_idle_timeout),
            str(response.content))
        self.assertContains(
            response,
            '<label for="id_user_idle_timeout">User idle timeout:</label>')
        self.assertContains(
            response,
            str('<input type="text" name="user_idle_timeout" size="50" '
                'required id="id_user_idle_timeout">'))
