from unittest.mock import patch, PropertyMock

from django.conf import settings

from tally_ho.libs.tests.test_base import (TestBase, create_center,
                                           create_reconciliation_form,
                                           create_result_form, create_station,
                                           create_tally)
from tally_ho.libs.verify.quarantine_checks import (
    create_quarantine_checks,
    pass_reconciliation_check,
    pass_over_voting_check,
    pass_card_check
)


class TestQuarantineChecks(TestBase):
    def setUp(self):  
        self.tally = create_tally()      
        create_quarantine_checks(tally_id=self.tally.pk,quarantine_data=getattr(settings, "QUARANTINE_DATA"))
        self._create_permission_groups()
        self._create_and_login_user()

    def test_pass_reconciliation_check(self):
        """Test the pass_reconciliation_check function.

        This test checks that Field 5 (The number of ballot papers in box)
        equals Total Candidates Votes + Field 4 (Number of Invalid ballot
        papers including blank ones).
        """
        # Setup
        center = create_center(tally=self.tally)
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

    def test_pass_reconciliation_check_with_default_tolerance(self):
        """Test the pass_reconciliation_check function

        This test checks that the pass_reconciliation_check function
        with default 3% tolerance."""
        center = create_center(tally=self.tally)
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )

        # Create reconciliation form
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=20,
            number_sorted_and_counted=100,
        )

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=80)
        ):
            # Test exact match: 100 = 80 + 20
            recon_form.number_sorted_and_counted = 100
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test within 3% tolerance: |101 - 100| = 1 <= 3% of 100 = 3
            recon_form.number_sorted_and_counted = 101
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test within 3% tolerance: |99 - 100| = 1 <= 3% of 100 = 3
            recon_form.number_sorted_and_counted = 99
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test at 3% tolerance limit: |103 - 100| = 3 <= 3% of 100 = 3
            recon_form.number_sorted_and_counted = 103
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test exceeding 3% tolerance: |104 - 100| = 4 > 3% of 100 = 3
            recon_form.number_sorted_and_counted = 104
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

            # Test other direction exceeding tolerance:
            # |96 - 100| = 4 > 3% of 100 = 3
            recon_form.number_sorted_and_counted = 96
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_reconciliation_check_with_tolerance(self, MockQC):
        """Test the pass_reconciliation_check function with tolerance."""
        center = create_center(tally=self.tally)
        station = create_station(center=center, registrants=100)
        result_form = create_result_form(
            center=center, station_number=station.station_number
        )

        # Create reconciliation form
        recon_form = create_reconciliation_form(
            result_form=result_form,
            user=self.user,
            number_invalid_votes=20,
            number_sorted_and_counted=100,
        )

        # Test 1: Value tolerance
        # Set tolerance to 5 votes
        MockQC.objects.get.return_value.value = 5
        MockQC.objects.get.return_value.percentage = 0

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=80)
        ):
            # Test exact match: 100 = 80 + 20
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test within tolerance: |105 - 100| = 5 <= 5
            recon_form.number_sorted_and_counted = 105
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test other direction: |95 - 100| = 5 <= 5
            recon_form.number_sorted_and_counted = 95
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test exceeding tolerance: |106 - 100| = 6 > 5
            recon_form.number_sorted_and_counted = 106
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

        # Test 2: Percentage tolerance
        # Set 10% tolerance on expected total (100)
        MockQC.objects.get.return_value.value = 0
        MockQC.objects.get.return_value.percentage = 10

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=80)
        ):
            # Expected total = 80 + 20 = 100, tolerance = 10% of 100 = 10
            # Test within tolerance: |110 - 100| = 10 <= 10
            recon_form.number_sorted_and_counted = 110
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test exceeding tolerance: |111 - 100| = 11 > 10
            recon_form.number_sorted_and_counted = 111
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_reconciliation_check(result_form))

        # Test 3: Value takes priority over percentage
        MockQC.objects.get.return_value.value = 3
        MockQC.objects.get.return_value.percentage = 20  # Would be 20

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=80)
        ):
            # Test at value limit: |103 - 100| = 3 <= 3
            recon_form.number_sorted_and_counted = 103
            recon_form.save()
            result_form.reload()
            self.assertTrue(pass_reconciliation_check(result_form))

            # Test exceeding value but within percentage: |104 - 100| = 4 > 3
            recon_form.number_sorted_and_counted = 104
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
        center = create_center(tally=self.tally)
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

        # Test when station has no registrants BUT reconciliation form exists
        # This should return True (check passes/skipped)
        station.registrants = None
        station.save()
        result_form.reload()
        self.assertTrue(pass_over_voting_check(result_form))

    @patch("tally_ho.libs.verify.quarantine_checks.QuarantineCheck")
    def test_pass_over_voting_check_with_custom_tolerance(self, MockQC):
        """Test the pass_over_voting_check function with custom tolerance."""
        center = create_center(tally=self.tally)
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

        # Test 1: Value tolerance
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

        # Test 2: Percentage tolerance
        # Set 10% tolerance on 100 registrants = 10 tolerance
        MockQC.objects.get.return_value.value = 0
        MockQC.objects.get.return_value.percentage = 10

        recon_form.number_invalid_votes = 10
        recon_form.save()
        result_form.reload()

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=95)
        ):
            # Test within limits: 105 <= 110 (100 + 10% of 100)
            self.assertTrue(pass_over_voting_check(result_form))

            # Test exceeding limit: 111 > 110
            recon_form.number_invalid_votes = 16
            recon_form.save()
            result_form.reload()
            self.assertFalse(pass_over_voting_check(result_form))

        # Test 3: Value takes priority over percentage
        # Set both value and percentage, value should be used
        MockQC.objects.get.return_value.value = 5
        MockQC.objects.get.return_value.percentage = 20  # Would be 20

        recon_form.number_invalid_votes = 0
        recon_form.save()
        result_form.reload()

        with patch.object(
            type(result_form), 'num_votes', PropertyMock(return_value=100)
        ):
            # Test at limit: 100 <= 105 (using value=5, not percentage=20)
            self.assertTrue(pass_over_voting_check(result_form))

            # Test exceeding value tolerance but within percentage: 106 > 105
            recon_form.number_invalid_votes = 6
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
        center = create_center(tally=self.tally)
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
        center = create_center(tally=self.tally)
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

        # Test 1: Percentage tolerance
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

        # Test 2: Value tolerance
        # Set custom tolerance to 8 votes
        MockQC.objects.get.return_value.value = 8
        MockQC.objects.get.return_value.percentage = 0

        recon_form.number_valid_votes = 88
        recon_form.number_invalid_votes = 15
        recon_form.save()
        result_form.reload()

        # Test within limits: 103 <= 108 (100 + 8)
        self.assertTrue(pass_card_check(result_form))

        # Test exceeding limit: 109 > 108
        recon_form.number_valid_votes = 94
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_card_check(result_form))

        # Test 3: Value takes priority over percentage
        # Set both value and percentage, value should be used
        MockQC.objects.get.return_value.value = 5
        MockQC.objects.get.return_value.percentage = 15  # Would be 15

        recon_form.number_valid_votes = 90
        recon_form.number_invalid_votes = 15
        recon_form.save()
        result_form.reload()

        # Test at limit: 105 <= 105 (using value=5, not percentage=15)
        self.assertTrue(pass_card_check(result_form))

        # Test exceeding value tolerance but within percentage: 106 > 105
        recon_form.number_valid_votes = 91
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_card_check(result_form))
