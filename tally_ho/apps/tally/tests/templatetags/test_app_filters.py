from django.test import TestCase

from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.templatetags.app_filters import \
    forms_processed_per_hour, get_quarantine_details
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_reconciliation_form,
    create_result_form,
    create_station,
    create_tally,
    create_candidates,
    create_center
)


class TestAppFilters(TestCase):
    def test_forms_processed_per_hour(self):
        self.assertEqual(forms_processed_per_hour(0, 0), 0)
        self.assertEqual(forms_processed_per_hour(420, 59), 420)
        self.assertEqual(forms_processed_per_hour(80085, 35119), 8209.4)


class TestGetQuarantineDetails(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        self.tally.users.add(self.user)

    def test_get_quarantine_details_returns_none_when_no_result_form(self):
        """Test filter returns None when result_form is None."""
        check = QuarantineCheck.objects.create(
            name="Test Check",
            method="pass_reconciliation_check",
            value=5,
            percentage=0
        )

        result = get_quarantine_details(None, check)

        self.assertIsNone(result)

    def test_get_quarantine_details_returns_none_when_no_check(self):
        """Test filter returns None when check is None."""
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=self.tally
        )

        result = get_quarantine_details(result_form, None)

        self.assertIsNone(result)

    def test_get_quarantine_details_calls_quarantine_checks_method(self):
        """Test filter correctly calls
        quarantine_checks.get_quarantine_check_details()."""
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=self.tally
        )

        create_reconciliation_form(
            result_form,
            self.user,
            number_invalid_votes=10,
            number_sorted_and_counted=110
        )

        create_candidates(
            result_form=result_form,
            user=result_form.user,
            votes=23,
            num_results=2
        )
        result_form.save()

        check = QuarantineCheck.objects.create(
            name="Reconciliation Check",
            method="pass_reconciliation_check",
            value=5,
            percentage=0
        )

        details = get_quarantine_details(result_form, check)

        self.assertIsNotNone(details)
        self.assertEqual(details['num_votes'], 92)
        self.assertEqual(details['invalid_votes'], 10)
        self.assertEqual(details['expected_total'], 102)
        self.assertEqual(details['actual_total'], 110)
        self.assertEqual(details['difference'], 8)

    def test_get_quarantine_details_with_over_voting_check(self):
        """Test filter works with over voting check."""
        center = create_center("12345", tally=self.tally)
        station = create_station(
            registrants=500, tally=self.tally, center=center
        )
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=self.tally,
            station_number=station.station_number,
            center=center
        )

        create_reconciliation_form(
            result_form,
            self.user,
            number_invalid_votes=30
        )

        create_candidates(
            result_form=result_form,
            user=result_form.user,
            votes=120,
            num_results=2
        )
        result_form.save()

        check = QuarantineCheck.objects.create(
            name="Over Voting Check",
            method="pass_over_voting_check",
            value=10,
            percentage=0
        )

        details = get_quarantine_details(result_form, check)

        self.assertIsNotNone(details)
        self.assertEqual(details['registrants'], 500)
        self.assertEqual(details['total_votes'], 510)
        self.assertEqual(details['max_allowed'], 510)

    def test_get_quarantine_details_with_card_check(self):
        """Test filter works with card check."""
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=self.tally
        )

        create_reconciliation_form(
            result_form,
            self.user,
            number_valid_votes=200,
            number_invalid_votes=15,
            number_of_voter_cards_in_the_ballot_box=210
        )

        check = QuarantineCheck.objects.create(
            name="Card Check",
            method="pass_card_check",
            value=8,
            percentage=0
        )

        details = get_quarantine_details(result_form, check)

        self.assertIsNotNone(details)
        self.assertEqual(details['voter_cards'], 210)
        self.assertEqual(details['total_ballot_papers'], 215)
        self.assertEqual(details['max_allowed'], 218)
