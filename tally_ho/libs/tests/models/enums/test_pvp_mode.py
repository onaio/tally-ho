from django.test import TestCase

from tally_ho.libs.models.enums.pvp_mode import PvpMode


class TestPvpMode(TestCase):
    def test_disabled_value(self):
        self.assertEqual(PvpMode.DISABLED.value, 0)

    def test_de1_only_value(self):
        self.assertEqual(PvpMode.DE1_ONLY.value, 1)

    def test_de1_and_de2_value(self):
        self.assertEqual(PvpMode.DE1_AND_DE2.value, 2)

    def test_label_disabled(self):
        self.assertEqual(PvpMode.DISABLED.label, "Disabled")

    def test_label_de1_only(self):
        self.assertEqual(PvpMode.DE1_ONLY.label, "De1 Only")

    def test_label_de1_and_de2(self):
        self.assertEqual(PvpMode.DE1_AND_DE2.label, "De1 And De2")

    def test_member_count(self):
        self.assertEqual(len(PvpMode), 3)
