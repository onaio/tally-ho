from django.test import TestCase

from tally_ho.apps.tally.forms.center_details_form import CenterDetailsForm
from tally_ho.libs.tests.test_base import (create_ballot, create_center,
                                           create_electrol_race,
                                           create_station,
                                           create_sub_constituency,
                                           create_tally)


class TestCenterDetailsForm(TestCase):
    def setUp(self):
        self.tally = create_tally()

    def test_center_details_form_valid(self):
        """Test form with valid center and station numbers."""
        center = create_center(code="12345", tally=self.tally)
        station = create_station(center=center, station_number=1)
        sub_constituency = create_sub_constituency(tally=self.tally)
        station.sub_constituency = sub_constituency
        station.save()

        # Create active ballot and add to sub_constituency
        ballot = create_ballot(tally=self.tally, active=True)
        sub_constituency.ballots.add(ballot)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": station.station_number,
            "station_number_copy": station.station_number,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_center_numbers_do_not_match(self):
        """Test form validation when center numbers don't match."""
        form_data = {
            "center_number": 12345,
            "center_number_copy": 54321,
            "station_number": 1,
            "station_number_copy": 1,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Center Numbers do not match", str(form.errors))

    def test_station_numbers_do_not_match(self):
        """Test form validation when station numbers don't match."""
        form_data = {
            "center_number": 12345,
            "center_number_copy": 12345,
            "station_number": 1,
            "station_number_copy": 2,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Station Numbers do not match", str(form.errors))

    def test_center_does_not_exist(self):
        """Test form validation when center doesn't exist."""
        form_data = {
            "center_number": 99999,
            "center_number_copy": 99999,
            "station_number": 1,
            "station_number_copy": 1,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Center Number does not exist", str(form.errors))

    def test_invalid_station_number_for_center(self):
        """Test form validation when station number is invalid for center."""
        center = create_center(code="12345", tally=self.tally)
        create_station(center=center, station_number=1)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": 99,  # Invalid station number
            "station_number_copy": 99,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Invalid Station Number for this Center", str(form.errors)
        )

    def test_center_is_disabled(self):
        """Test form validation when center is disabled."""
        center = create_center(code="12345", tally=self.tally, active=False)
        create_station(center=center, station_number=1)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": 1,
            "station_number_copy": 1,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Center is disabled", str(form.errors))

    def test_station_is_disabled(self):
        """Test form validation when station is disabled."""
        center = create_center(code="12345", tally=self.tally)
        station = create_station(center=center, station_number=1, active=False)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": station.station_number,
            "station_number_copy": station.station_number,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Station is disabled", str(form.errors))

    def test_station_does_not_exist(self):
        """Test form validation when station doesn't exist."""
        center = create_center(code="12345", tally=self.tally)
        # Create station with number 1, but try to access station 2
        create_station(center=center, station_number=1)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": 2,  # Station doesn't exist
            "station_number_copy": 2,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        # This actually triggers "Invalid Station Number for this Center" first
        self.assertIn(
            "Invalid Station Number for this Center", str(form.errors)
        )

    def test_all_municipality_races_disabled(self):
        """Test form validation when all municipality races are inactive."""
        center = create_center(code="12345", tally=self.tally)
        station = create_station(center=center, station_number=1)
        sub_constituency = create_sub_constituency(tally=self.tally)
        station.sub_constituency = sub_constituency
        station.save()

        # Create both List and Individual races as inactive
        list_race = create_electrol_race(
            tally=self.tally,
            election_level="Municipality",
            ballot_name="List"
        )
        individual_race = create_electrol_race(
            tally=self.tally,
            election_level="Municipality",
            ballot_name="Individual"
        )
        list_ballot = create_ballot(
            tally=self.tally, electrol_race=list_race, active=False
        )
        individual_ballot = create_ballot(
            tally=self.tally, electrol_race=individual_race, active=False
        )
        sub_constituency.ballots.add(list_ballot, individual_ballot)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": station.station_number,
            "station_number_copy": station.station_number,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Race is disabled.", str(form.errors))

    def test_one_municipality_race_active(self):
        """Test form validation when one race is active, one inactive."""
        center = create_center(code="12345", tally=self.tally)
        station = create_station(center=center, station_number=1)
        sub_constituency = create_sub_constituency(tally=self.tally)
        station.sub_constituency = sub_constituency
        station.save()

        # Create municipality scenario: Individual active, List inactive
        list_race = create_electrol_race(
            tally=self.tally,
            election_level="Municipality",
            ballot_name="List"
        )
        individual_race = create_electrol_race(
            tally=self.tally,
            election_level="Municipality",
            ballot_name="Individual"
        )
        list_ballot = create_ballot(
            tally=self.tally, electrol_race=list_race, active=False
        )
        individual_ballot = create_ballot(
            tally=self.tally, electrol_race=individual_race, active=True
        )
        sub_constituency.ballots.add(list_ballot, individual_ballot)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": station.station_number,
            "station_number_copy": station.station_number,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        # Should pass - at least one race active
        self.assertTrue(form.is_valid())

    def test_all_ballots_active(self):
        """Test form validation when all ballots are active."""
        center = create_center(code="12345", tally=self.tally)
        station = create_station(center=center, station_number=1)
        sub_constituency = create_sub_constituency(tally=self.tally)
        station.sub_constituency = sub_constituency
        station.save()

        # Create multiple active ballots with different electrol races
        electrol_race1 = create_electrol_race(
            tally=self.tally,
            election_level="Municipality",
            ballot_name="Active Race 1"
        )
        electrol_race2 = create_electrol_race(
            tally=self.tally,
            election_level="Municipality",
            ballot_name="Active Race 2"
        )
        ballot1 = create_ballot(
            tally=self.tally, electrol_race=electrol_race1, active=True
        )
        ballot2 = create_ballot(
            tally=self.tally, electrol_race=electrol_race2, active=True
        )
        sub_constituency.ballots.add(ballot1, ballot2)

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": station.station_number,
            "station_number_copy": station.station_number,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_station_with_no_ballots(self):
        """Test form validation when sub_constituency has no ballots."""
        center = create_center(code="12345", tally=self.tally)
        station = create_station(center=center, station_number=1)
        # create_station creates a sub_constituency but with no ballots

        form_data = {
            "center_number": center.code,
            "center_number_copy": center.code,
            "station_number": station.station_number,
            "station_number_copy": station.station_number,
            "tally_id": self.tally.pk,
        }

        form = CenterDetailsForm(data=form_data)
        # Should fail validation when no ballots are available
        self.assertFalse(form.is_valid())
        self.assertIn("Race is disabled.", str(form.errors))

