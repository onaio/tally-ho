from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.verify.quarantine_checks import\
    create_quarantine_checks, pass_overvote, pass_tampering
from tally_ho.libs.tests.test_base import create_candidates,\
    create_center, create_reconciliation_form, create_result_form,\
    create_station, TestBase


class TestQuarantineChecks(TestBase):
    def setUp(self):
        create_quarantine_checks()
        self._create_permission_groups()
        self._create_and_login_user()

    def test_pass_overvote_true_no_registrants(self):
        """Test pass overvote returns true with no registrants"""
        center = create_center()
        create_station(center=center)
        result_form = create_result_form(center=center,
                                         form_state=FormState.ARCHIVED)
        self.assertEqual(pass_overvote(result_form), True)

    def test_pass_overvote_true_no_recon(self):
        """Test pass overvote returns true with no recon form"""
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center,
                                         form_state=FormState.ARCHIVED)
        self.assertEqual(pass_overvote(result_form), True)

    def test_pass_overvote_true(self):
        """Test pass overvote returns true"""
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center,
                                         form_state=FormState.ARCHIVED)
        create_reconciliation_form(result_form, self.user)
        self.assertEqual(pass_overvote(result_form), True)

    def test_pass_overvote_false(self):
        """Test pass overvote returns false"""
        center = create_center()
        station = create_station(center=center, registrants=1)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
            form_state=FormState.ARCHIVED)
        create_reconciliation_form(result_form,
                                   self.user,
                                   number_unstamped_ballots=11)
        self.assertEqual(pass_overvote(result_form), False)

    def test_pass_tamper_true_no_registrants(self):
        """Test pass tampering returns true with no registrants"""
        center = create_center()
        create_station(center=center)
        result_form = create_result_form(center=center,
                                         form_state=FormState.ARCHIVED)
        self.assertEqual(pass_tampering(result_form), True)

    def test_pass_tamper_true_no_recon(self):
        """Test pass tampering returns true with no recon form"""
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center,
                                         form_state=FormState.ARCHIVED)
        self.assertEqual(pass_tampering(result_form), True)

    def test_pass_tampering_true(self):
        """Test pass tampering returns true"""
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center,
                                         form_state=FormState.ARCHIVED)
        create_reconciliation_form(result_form,
                                   self.user,
                                   number_unstamped_ballots=0)
        self.assertEqual(pass_tampering(result_form), True)

    def test_pass_tampering_true_diff(self):
        """Test pass tampering returns true difference"""
        center = create_center()
        create_station(center=center,
                       registrants=1)
        result_form = create_result_form(center=center,
                                         form_state=FormState.ARCHIVED)
        create_candidates(result_form, self.user, num_results=1)
        create_reconciliation_form(result_form,
                                   self.user,
                                   number_ballots_inside_box=250,
                                   number_unstamped_ballots=0)
        self.assertEqual(pass_tampering(result_form), True)
