from django.test import TestCase

from tally_ho.apps.tally.templatetags.app_filters import \
    forms_processed_per_hour


class TestAppFilters(TestCase):
    def test_forms_processed_per_hour(self):
        self.assertEqual(forms_processed_per_hour(0, 0), 0)
        self.assertEqual(forms_processed_per_hour(420, 59), 420)
        self.assertEqual(forms_processed_per_hour(80085, 35119), 8209.4)
