from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.tests.test_base import TestBase


class TestTally(TestBase):
    def test_pvp_mode_defaults_to_disabled(self):
        tally = Tally.objects.create(name="t1")
        tally.refresh_from_db()
        self.assertEqual(tally.pvp_mode, PvpMode.DISABLED)

    def test_pvp_mode_can_be_set_to_de1_only(self):
        tally = Tally.objects.create(name="t2", pvp_mode=PvpMode.DE1_ONLY)
        tally.refresh_from_db()
        self.assertEqual(tally.pvp_mode, PvpMode.DE1_ONLY)
