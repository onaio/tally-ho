from django.conf import settings
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.verify.quarantine_checks import (
    create_quarantine_checks,
    pass_registrants_trigger,
    pass_voter_cards_trigger,
    pass_ballot_papers_trigger,
    pass_ballot_inside_box_trigger,
    pass_candidates_votes_trigger
)
from tally_ho.libs.tests.test_base import create_candidates,\
    create_center, create_reconciliation_form, create_result_form,\
    create_station, TestBase, create_tally


class TestQuarantineChecks(TestBase):
    def setUp(self):
        create_quarantine_checks(getattr(settings, 'QUARANTINE_DATA'))
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
        station = create_station(center=center,
                       registrants=50)
        result_form = create_result_form(
            center=center,
            station_number=station.station_number)

        # Test when there is no reconciliation form
        self.assertTrue(pass_registrants_trigger(result_form))

        recon_form =\
            create_reconciliation_form(
                result_form=result_form,
                user=self.user,
                total_of_cancelled_ballots_and_ballots_inside_box=50
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
        recon_form.total_of_cancelled_ballots_and_ballots_inside_box = 70
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

        recon_form =\
            create_reconciliation_form(
                result_form=result_form,
                user=self.user,
                total_of_cancelled_ballots_and_ballots_inside_box=50,
                number_of_voter_cards_in_the_ballot_box=50,
            )

        # Test for equality
        self.assertTrue(pass_voter_cards_trigger(result_form))

        # Test for inequality
        recon_form.number_of_voter_cards_in_the_ballot_box = 51
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

        recon_form =\
            create_reconciliation_form(
                result_form=result_form,
                user=self.user,
                number_ballots_received=100,
                number_ballots_inside_and_outside_box=100,
            )

        # Test for equality
        self.assertTrue(pass_ballot_papers_trigger(result_form))

        # Test for inequality
        recon_form.number_ballots_inside_and_outside_box = 99
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

        recon_form =\
            create_reconciliation_form(
                result_form=result_form,
                user=self.user,
                number_unstamped_ballots=30,
                number_invalid_votes=20,
                number_valid_votes=50,
                number_ballots_inside_box=100,
            )

        # Test for equality
        self.assertTrue(pass_ballot_inside_box_trigger(result_form))

        # Test for inequality
        recon_form.number_ballots_inside_box = 99
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
            form_state=FormState.ARCHIVED
        )
        # Test when there is no reconciliation form
        self.assertTrue(pass_candidates_votes_trigger(result_form))

        recon_form =\
            create_reconciliation_form(
                result_form=result_form,
                user=self.user,
                number_sorted_and_counted=200,
            )
        votes = 100
        tally = create_tally()
        tally.users.add(self.user)
        create_candidates(
            result_form, votes=votes, user=self.user,
            num_results=1, tally=tally
        )

        # Test for equality
        self.assertTrue(pass_candidates_votes_trigger(result_form))

        # Test for inequality
        recon_form.number_sorted_and_counted = 100
        recon_form.save()
        result_form.reload()
        self.assertFalse(pass_candidates_votes_trigger(result_form))
