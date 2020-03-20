from django.conf import settings
from django.contrib.sites.models import Site
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_site_info,\
    create_tally, TestBase
from tally_ho.apps.tally.models.site_info import SiteInfo


class TestSiteInfo(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user,
                                groups.TALLY_MANAGER)

    def test_site_info(self):
        tally = create_tally()
        tally.users.add(self.user)

        user_idle_timeout = 60
        site_id = getattr(settings, "SITE_ID", None)
        site = Site.objects.get(pk=site_id)
        create_site_info(site, user_idle_timeout)

        # Test object name is site name hyphen user idle timeout
        site_info = SiteInfo.objects.get(id=1)
        expected_object_name =\
            f'{site_info.site.name} - {site_info.user_idle_timeout}'
        self.assertEquals(expected_object_name, str(site_info))
        self.assertEqual(site_info.user_idle_timeout, user_idle_timeout)
