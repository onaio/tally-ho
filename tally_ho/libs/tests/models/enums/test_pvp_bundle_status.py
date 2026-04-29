from django.test import TestCase

from tally_ho.libs.models.enums.pvp_bundle_status import PvpBundleStatus


class TestPvpBundleStatus(TestCase):
    def test_pending_value(self):
        self.assertEqual(PvpBundleStatus.PENDING.value, 0)

    def test_importing_value(self):
        self.assertEqual(PvpBundleStatus.IMPORTING.value, 1)

    def test_completed_value(self):
        self.assertEqual(PvpBundleStatus.COMPLETED.value, 2)

    def test_failed_value(self):
        self.assertEqual(PvpBundleStatus.FAILED.value, 3)

    def test_member_count(self):
        self.assertEqual(len(PvpBundleStatus), 4)
