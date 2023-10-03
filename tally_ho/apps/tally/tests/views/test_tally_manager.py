from django.conf import settings
from django.test import RequestFactory

from django.contrib.sites.models import Site
from tally_ho.apps.tally.models.site_info import SiteInfo
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.views import tally_manager as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    configure_messages,
    create_site_info,
    create_tally,
    TestBase,
)


class TestTallyManager(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

    def test_set_user_timeout_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.SetUserTimeOutView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        site_id = getattr(settings, "SITE_ID", None)

        try:
            Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            site = Site.objects.create(name="HENC RMS")
            site_id = site.id

        response = view(
            request,
            site_id=site_id)

        self.assertContains(response, '<h1>Set user idle timeout</h1>')
        self.assertContains(
            response,
            '<div class="form-instructions">Set timeout in minutes.</div>')

        user_idle_timeout = None
        try:
            siteinfo = SiteInfo.objects.get(site__pk=site_id)
            user_idle_timeout = siteinfo.user_idle_timeout
        except SiteInfo.DoesNotExist:
            user_idle_timeout = getattr(settings, 'DEFAULT_IDLE_TIMEOUT')

        self.assertIn(
            str('Current user idle timeout: '
                '{} minutes').format(user_idle_timeout),
            str(response.content))
        self.assertContains(
            response,
            '<label for="id_user_idle_timeout">User idle timeout:</label>')
        self.assertContains(
            response,
            str('<input type="text" name="user_idle_timeout" '
                'size="50" required id="id_user_idle_timeout">'))

    def test_edit_user_view_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        user = UserProfile.objects.create(
            username='john',
            first_name='doe',
            reset_password=False)
        view = views.EditUserView.as_view()
        request = self.factory.get('/')
        user_id = user.id
        request.user = self.user
        request.session = {}
        request.META =\
            {'HTTP_REFERER':
             f'super-admin/edit-user/{tally.id}/{user_id}/'}

        response = view(
            request,
            user_id=user_id,
            tally_id=tally.id)
        response.render()
        self.assertEqual(request.session['url_name'], 'user-tally-list')
        self.assertEqual(request.session['url_param'], tally.id)
        self.assertEqual(request.session['url_keyword'], 'tally_id')

        request.session = {}
        request.META = {'HTTP_REFERER': '/tally-manager/user-list/user'}

        response = view(
            request,
            user_id=user_id,
            tally_id=tally.id)
        response.render()
        self.assertEqual(request.session['url_name'], 'user-tally-list')
        self.assertEqual(request.session['url_keyword'], 'tally_id')

    def test_set_user_timeout_valid_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.SetUserTimeOutView.as_view()
        user_idle_timeout = 60
        data = {'user_idle_timeout': user_idle_timeout}
        request = self.factory.post('/', data=data)
        request.user = self.user
        configure_messages(request)

        site_id = getattr(settings, "SITE_ID", None)
        try:
            Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            site = Site.objects.create(name="HENC RMS")
            site_id = site.id
        response = view(request, site_id=site_id)

        success_url = 'tally-manager'
        siteinfo = SiteInfo.objects.get(site__pk=site_id)

        self.assertEqual(siteinfo.user_idle_timeout, user_idle_timeout)
        self.assertEqual(response.status_code, 302)
        self.assertIn(success_url,  response.url)

    def test_set_user_timeout_invalid_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.SetUserTimeOutView.as_view()
        user_idle_timeout = 'example'
        data = {'user_idle_timeout': user_idle_timeout}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}

        site_id = getattr(settings, "SITE_ID", None)
        site = None

        try:
            site = Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            site = Site.objects.create(name="HENC RMS")
            site_id = site.id

        create_site_info(site=site, user_idle_timeout=50)
        response = view(request, site_id=site_id)
        response.render()

        siteinfo = SiteInfo.objects.get(site__pk=site_id)
        self.assertNotEqual(response.status_code, 302)
        self.assertIn(
            str('Current user idle timeout: '
                '{} minutes').format(siteinfo.user_idle_timeout),
            str(response.content))
        self.assertContains(
            response,
            '<label for="id_user_idle_timeout">User idle timeout:</label>')
        self.assertContains(
            response,
            str('<input type="text" name="user_idle_timeout" value="example" '
                'size="50" required id="id_user_idle_timeout">'))
