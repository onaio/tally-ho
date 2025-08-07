from unittest.mock import patch, PropertyMock

from django.conf import settings

from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import (TestBase, create_candidates,
                                           create_center,
                                           create_reconciliation_form,
                                           create_result_form, create_station,
                                           create_tally)
from tally_ho.libs.verify.quarantine_checks import (
    create_quarantine_checks, pass_ballot_inside_box_trigger,
    pass_ballot_papers_trigger, pass_candidates_votes_trigger,
    pass_registrants_trigger, pass_voter_cards_trigger,
    pass_reconciliation_check, pass_over_voting_check, pass_card_check)


class TestQuarantineChecks(TestBase):
    def setUp(self):
        create_quarantine_checks(getattr(settings, "QUARANTINE_DATA"))
        self._create_permission_groups()
        self._create_and_login_user()

    def test_pass_registrants_trigger(self):
        """Test the pass_registrants_trigger function.

        This test checks that the total of cancelled ballots and
        ballots inside the box does not exceed the number of
        registered voters at the polling station.
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=50)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )

        # Test when there is no reconciliation form
        self.assertTrue(pass_registrants_trigger(result_form))

        recon_form = create_reconciliation_form(
            result_form=result_form, user=self.user, number_valid_votes=50
        )
        # Test when registrants are equal
        self.assertTrue(pass_registrants_trigger(result_form))
        # Test when registrants are less
        station.registrants = 40
        station.save()
        result_form.reload()
        self.assertFalse(pass_registrants_trigger(result_form))

        # Test when registrants exceed
        station.registrants = 60
        station.save()
        result_form.reload()
        self.assertTrue(pass_registrants_trigger(result_form))

        # Test when number of ballots exceeds registrants
        recon_form.number_valid_votes = 70
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_registrants_trigger(result_form))

    def test_pass_voter_cards_trigger(self):
        """Test the pass_voter_cards_trigger function.

        This test checks that the sum of cancelled ballots and
        ballots inside the box equals the number of voter cards
        in the ballot box.
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
        )
        # Test when there is no reconciliation form
        self.assertTrue(pass_voter_cards_trigger(result_form))

        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_valid_votes=50,
            number_invalid_votes=0,
            number_sorted_and_counted=50,
        )

        # Test for equality
        self.assertTrue(pass_voter_cards_trigger(result_form))

        # Test for inequality
        recon_form.number_sorted_and_counted = 51
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_voter_cards_trigger(result_form))

    def test_pass_ballot_papers_trigger(self):
        """Test the pass_ballot_papers_trigger function.

        This test checks that the total number of ballots received
        matches the total number of ballots found inside and outside
        the ballot box.
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
        )
        # Test when there is no reconciliation form
        self.assertTrue(pass_ballot_papers_trigger(result_form))

        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_of_voters=100,
            number_sorted_and_counted=100,
        )

        # Test for equality
        self.assertTrue(pass_ballot_papers_trigger(result_form))

        # Test for inequality
        recon_form.number_sorted_and_counted = 99
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_ballot_papers_trigger(result_form))

    def test_pass_ballot_inside_box_trigger(self):
        """Test the pass_ballot_inside_box_trigger function.

        This test checks that the total number of ballots found
        inside the ballot box equals the sum of unstamped ballots,
        invalid votes, and valid votes.
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
        )
        # Test when there is no reconciliation form
        self.assertTrue(pass_ballot_inside_box_trigger(result_form))

        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=20,
            number_valid_votes=50,
            number_sorted_and_counted=70,
        )

        # Test for equality
        self.assertTrue(pass_ballot_inside_box_trigger(result_form))

        # Test for inequality
        recon_form.number_sorted_and_counted = 99
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_ballot_inside_box_trigger(result_form))

    def test_pass_candidates_votes_trigger(self):
        """Test the pass_candidates_votes_trigger function.

        This test checks that the total number of sorted and counted
        ballots matches the total votes distributed among the candidates.
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
            form_state=FormState.ARCHIVED,
        )
        # Test when there is no reconciliation form
        self.assertTrue(pass_candidates_votes_trigger(result_form))

        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_valid_votes=200,
        )
        votes = 100
        tally = create_tally()
        tally.users.add(self.user)
        create_candidates(
            result_form,
            votes=votes,
            user=self.user,
            num_results=1,
            tally=tally,
        )

        # Test for equality
        self.assertTrue(pass_candidates_votes_trigger(result_form))

        # Test for inequality
        recon_form.number_valid_votes = 100
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_candidates_votes_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_registrants_trigger_with_tolerance_value(self, MockQC):
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        recon_form = create_reconciliation_form(
            result_form=result_form, user=self.user, number_valid_votes=105
        )
        # Set tolerance value to 5
        MockQC.objects.get.return_value.value = 5
        MockQC.objects.get.return_value.percentage = 0
        self.assertTrue(pass_registrants_trigger(result_form))
        # Exceed tolerance
        recon_form.number_valid_votes = 106
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_registrants_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_registrants_trigger_with_tolerance_percentage(self, MockQC):
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        recon_form = create_reconciliation_form(
            result_form=result_form, user=self.user, number_valid_votes=109
        )
        # Set tolerance percentage to 10%
        MockQC.objects.get.return_value.value = 0
        MockQC.objects.get.return_value.percentage = 10
        self.assertTrue(pass_registrants_trigger(result_form))
        # Exceed tolerance
        recon_form.number_valid_votes = 111
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_registrants_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_voter_cards_trigger_with_tolerance_value(self, MockQC):
        """Test the pass_voter_cards_trigger function with tolerance
        value.

        This test checks that the sum of cancelled ballots and
        ballots inside the box equals the number of voter cards
        in the ballot box.
        """
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_valid_votes=100,
            number_invalid_votes=0,
            number_sorted_and_counted=100,
        )
        MockQC.objects.get.return_value.value = 5
        MockQC.objects.get.return_value.percentage = 0
        self.assertTrue(pass_voter_cards_trigger(result_form))
        recon_form.number_sorted_and_counted = 106
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_voter_cards_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_voter_cards_trigger_with_tolerance_percentage(self, MockQC):
        """Test the pass_voter_cards_trigger function with tolerance
        percentage.

        This test checks that the sum of cancelled ballots and
        ballots inside the box equals the number of voter cards
        in the ballot box.
        """
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_valid_votes=100,
            number_invalid_votes=0,
            number_sorted_and_counted=100,
        )
        MockQC.objects.get.return_value.value = 0
        MockQC.objects.get.return_value.percentage = 10
        self.assertTrue(pass_voter_cards_trigger(result_form))
        recon_form.number_sorted_and_counted = 115
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_voter_cards_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_ballot_papers_trigger_with_tolerance_value(self, MockQC):
        """Test the pass_ballot_papers_trigger function with tolerance
        value.

        This test checks that the total number of ballots received
        matches the total number of ballots found inside and outside
        the ballot box.
        """
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_of_voters=105,
            number_sorted_and_counted=100,
        )
        MockQC.objects.get.return_value.value = 5
        MockQC.objects.get.return_value.percentage = 0
        self.assertTrue(pass_ballot_papers_trigger(result_form))
        recon_form.number_of_voters = 106
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_ballot_papers_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_ballot_papers_trigger_with_tolerance_percentage(
        self, MockQC
    ):
        """Test the pass_ballot_papers_trigger function with tolerance
        percentage.

        This test checks that the total number of ballots received
        matches the total number of ballots found inside and outside
        the ballot box.
        """
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_of_voters=110,
            number_sorted_and_counted=100,
        )
        MockQC.objects.get.return_value.value = 0
        MockQC.objects.get.return_value.percentage = 10
        self.assertTrue(pass_ballot_papers_trigger(result_form))
        recon_form.number_of_voters = 112
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_ballot_papers_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_candidates_votes_trigger_with_tolerance_value(self, MockQC):
        """Test the pass_candidates_votes_trigger function with tolerance
        value.

        This test checks that the total number of sorted and counted
        ballots matches the total votes distributed among the candidates.
        """
        tally = create_tally()
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        create_candidates(
            result_form, votes=50, user=self.user, num_results=1, tally=tally
        )
        recon_form = create_reconciliation_form(
            result_form=result_form, user=self.user, number_valid_votes=100
        )
        recon_form.number_valid_votes = 105
        recon_form.save()
        result_form.reload()
        MockQC.objects.get.return_value.value = 5
        MockQC.objects.get.return_value.percentage = 0
        self.assertTrue(pass_candidates_votes_trigger(result_form))
        recon_form.number_valid_votes = 106
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_candidates_votes_trigger(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_candidates_votes_trigger_with_tolerance_percentage(
        self, MockQC
    ):
        """Test the pass_candidates_votes_trigger function with tolerance
        percentage.

        This test checks that the total number of sorted and counted
        ballots matches the total votes distributed among the candidates.
        """
        tally = create_tally()
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )
        create_candidates(
            result_form, votes=50, user=self.user, num_results=1, tally=tally
        )
        recon_form = create_reconciliation_form(
            result_form=result_form, user=self.user, number_valid_votes=100
        )
        recon_form.number_valid_votes = 110
        recon_form.save()
        result_form.reload()
        MockQC.objects.get.return_value.value = 0
        MockQC.objects.get.return_value.percentage = 10
        self.assertTrue(pass_candidates_votes_trigger(result_form))
        recon_form.number_valid_votes = 112
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_candidates_votes_trigger(result_form))

    def test_pass_reconciliation_check(self):
        """Test the pass_reconciliation_check function.

        This test checks that Field 5 (The number of ballot papers in box)
        equals Total Candidates Votes + Field 4 (Number of Invalid ballot
        papers including blank ones).
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
        )

        # Test when there is no reconciliation form
        self.assertTrue(pass_reconciliation_check(result_form))

        # Create reconciliation form with matching values
        # Field 5 = 100, Field 4 = 20, Total Candidates Votes = 80
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=20,  # Field 4
            number_sorted_and_counted=100,  # Field 5
        )

        # Mock the result form to have 80 total votes
        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=80)
        ):
            # Test for equality: 100 = 80 + 20
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test for inequality: 100 != 80 + 25
            recon_form.number_invalid_votes = 25
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

            # Test for inequality: 105 != 80 + 20
            recon_form.number_invalid_votes = 20
            recon_form.number_sorted_and_counted = 105
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

    def test_pass_reconciliation_check_exact_match(self):
        """Test the pass_reconciliation_check function requires exact match."""
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )

        # Create reconciliation form
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=20,
            number_sorted_and_counted=101,  # 1 more than expected
        )

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=80)
        ):
            # Test exact match: 100 = 80 + 20
            recon_form.number_sorted_and_counted = 100
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test even 1 difference fails: 101 vs 80 + 20 = 100
            recon_form.number_sorted_and_counted = 101
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

            # Test another difference: 99 vs 80 + 20 = 100
            recon_form.number_sorted_and_counted = 99
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

    def test_pass_over_voting_check(self):
        """Test the pass_over_voting_check function.

        This test checks that the total number of people who voted does not
        exceed the number of registered voters plus tolerance for staff and
        security.
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
        )

        # Test when there is no reconciliation form
        self.assertTrue(pass_over_voting_check(result_form))

        # Test when station has no registrants
        station.registrants = None
        station.save()
        result_form.reload()
        self.assertTrue(pass_over_voting_check(result_form))

        # Reset registrants
        station.registrants = 100
        station.save()
        result_form.reload()

        # Create reconciliation form with valid voting numbers
        # Total votes: 80 + 15 = 95, Max allowed: 100 + 5 = 105
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=15,  # Field 4
        )

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=80)
        ):
            # Test within limits: 95 <= 105
            self.assertTrue(pass_over_voting_check(result_form))

            # Test at the limit: 105 <= 105
            recon_form.number_invalid_votes = 20
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_over_voting_check(result_form))

            # Test exceeding limit: 101 > 105 (should pass since 101 <= 105)
            # Let's test with a value that actually exceeds: 106 > 105
            recon_form.number_invalid_votes = 26
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_over_voting_check(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_over_voting_check_with_custom_tolerance(self, MockQC):
        """Test the pass_over_voting_check function with custom tolerance."""
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )

        # Create reconciliation form
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=10,
        )

        # Set custom tolerance to 10
        MockQC.objects.get.return_value.value = 10
        MockQC.objects.get.return_value.percentage = 0

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=95)
        ):
            # Test within limits: 105 <= 110
            self.assertTrue(pass_over_voting_check(result_form))

            # Test exceeding limit: 106 <= 110 (should pass)
            # Let's test with a value that actually exceeds: 111 > 110
            recon_form.number_invalid_votes = 16
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_over_voting_check(result_form))

    def test_pass_card_check(self):
        """Test the pass_card_check function.

        This test checks that the total number of ballot papers
        (valid + invalid) does not exceed the number of voter cards plus
        tolerance value.
        """
        # Setup
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number,
        )

        # Test when there is no reconciliation form
        self.assertTrue(pass_card_check(result_form))

        # Create reconciliation form with valid numbers
        # Voter cards: 100, Valid votes: 80, Invalid votes: 15
        # Total ballot papers: 95, Max allowed: 100 + 5% = 105
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_valid_votes=80,  # Field 3
            number_invalid_votes=15,  # Field 4
            number_of_voter_cards_in_the_ballot_box=100,  # Field 2
        )

        # Test within limits: 95 <= 105
        self.assertTrue(pass_card_check(result_form))

        # Test at the limit: 105 <= 105
        recon_form.number_valid_votes = 90
        recon_form.save()
        result_form.reload()
        self.assertTrue(pass_card_check(result_form))

        # Test exceeding limit: 106 > 105
        recon_form.number_valid_votes = 91
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_card_check(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_card_check_with_custom_tolerance(self, MockQC):
        """Test the pass_card_check function with custom tolerance."""
        center = create_center()
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )

        # Create reconciliation form
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_valid_votes=80,
            number_invalid_votes=15,
            number_of_voter_cards_in_the_ballot_box=100,
        )

        # Set custom tolerance to 10%
        MockQC.objects.get.return_value.percentage = 10
        MockQC.objects.get.return_value.value = 0

        # Test within limits: 95 <= 110
        self.assertTrue(pass_card_check(result_form))

        # Test exceeding limit: 111 > 110
        recon_form.number_valid_votes = 96
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_card_check(result_form))
