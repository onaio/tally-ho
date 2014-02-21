from libya_tally.libs.verify.quarantine_checks import\
    create_quarantine_checks, pass_overvote, pass_tampering
from libya_tally.libs.tests.test_base import create_candidates, create_center,\
    create_reconciliation_form, create_result_form, create_station, TestBase


class TestQuarantineChecks(TestBase):
    def setUp(self):
        create_quarantine_checks()
        self._create_permission_groups()
        self._create_and_login_user()

    def test_pass_overvote_true_no_registrants(self):
        center = create_center()
        create_station(center=center)
        result_form = create_result_form(center=center)
        self.assertEqual(pass_overvote(result_form), True)

    def test_pass_overvote_true_no_recon(self):
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center)
        self.assertEqual(pass_overvote(result_form), True)

    def test_pass_overvote_true(self):
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center)
        create_reconciliation_form(result_form, self.user)
        self.assertEqual(pass_overvote(result_form), True)

    def test_pass_overvote_false(self):
        center = create_center()
        station = create_station(center=center, registrants=1)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number)
        create_reconciliation_form(result_form,
                                   self.user,
                                   number_unstamped_ballots=11)
        self.assertEqual(pass_overvote(result_form), False)

    def test_pass_tamper_true_no_registrants(self):
        center = create_center()
        create_station(center=center)
        result_form = create_result_form(center=center)
        self.assertEqual(pass_tampering(result_form), True)

    def test_pass_tamper_true_no_recon(self):
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center)
        self.assertEqual(pass_tampering(result_form), True)

    def test_pass_tampering_true(self):
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center)
        create_reconciliation_form(result_form,
                                   self.user,
                                   number_unstamped_ballots=0)
        self.assertEqual(pass_tampering(result_form), True)

    def test_pass_tampering_true_diff(self):
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center)
        create_candidates(result_form, self.user, num_results=1)
        create_reconciliation_form(result_form,
                                   self.user,
                                   number_ballots_inside_box=250,
                                   number_unstamped_ballots=0)
        self.assertEqual(pass_tampering(result_form), True)
