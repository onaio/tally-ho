from tally_ho.apps.tally.forms.site_info_form import SiteInfoForm
from tally_ho.apps.tally.models.site_info import SiteInfo
from tally_ho.libs.tests.test_base import TestBase


class SiteInfoFormTest(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_blank_data(self):
        form = SiteInfoForm({})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            'user_idle_timeout': ['This field is required.'],
        })

    def test_invalid_data(self):
        user_idle_timeout = 'example'
        form = SiteInfoForm({'user_idle_timeout': user_idle_timeout})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            'user_idle_timeout': ['Enter a whole number.'],
        })

    def test_valid_data(self):
        user_idle_timeout = 60
        form = SiteInfoForm({'user_idle_timeout': user_idle_timeout})
        self.assertTrue(form.is_valid())
        site_info = form.save()
        self.assertEqual(site_info.user_idle_timeout, user_idle_timeout)

    def test_site_info_update(self):
        user_idle_timeout = 60
        old_form = SiteInfoForm({'user_idle_timeout': user_idle_timeout})
        old_form.save()
        new_form = SiteInfoForm({'user_idle_timeout': 50})
        site_info = new_form.save()
        site_info_count = SiteInfo.objects.count()
        self.assertNotEqual(site_info.user_idle_timeout, user_idle_timeout)
        self.assertEqual(site_info.user_idle_timeout, 50)
        self.assertEqual(site_info_count, 1)
