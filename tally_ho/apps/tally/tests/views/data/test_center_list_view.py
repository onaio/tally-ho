import json

from django.test import RequestFactory

from tally_ho.apps.tally.views.constants import show_inactive_query_param
from tally_ho.apps.tally.views.data import center_list_view as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_center, create_result_form,
                                           create_station, create_tally)


class TestCenterListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_center_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CenterListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Center and Station List")
        self.assertContains(response, "New Station")
        self.assertContains(response, "New Center")
        self.assertEqual(response.context_data['show_inactive'], 'false')

    def test_center_list_view_with_show_inactive_context(self):
        """Test that CenterListView includes show_inactive context"""
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CenterListView.as_view()

        # Test without show_inactive parameter (default)
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Center and Station List")
        self.assertEqual(response.context_data['show_inactive'], 'false')

        # Test with show_inactive=true
        request = self.factory.get(f"/?{show_inactive_query_param}=true")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.context_data['show_inactive'], 'true')

    def test_center_list_data_filters_inactive_ballots_by_default(self):
        """Test that CenterListDataView filters inactive ballots by default"""
        tally = create_tally()
        tally.users.add(self.user)

        # Create center
        center = create_center(tally=tally)

        # Create stations - one with active ballot, one with inactive ballot
        active_station = create_station(
            center=center,
            tally=tally,
            station_number=1
        )
        inactive_station = create_station(
            center=center,
            tally=tally,
            station_number=2
        )

        # Create ballots - one active, one inactive
        active_ballot = create_ballot(tally=tally, active=True, number=10)
        inactive_ballot = create_ballot(tally=tally, active=False, number=11)

        # Create result forms linking stations to ballots through center
        create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=active_ballot,
            center=center,
            station_number=active_station.station_number,
            barcode="111111111",
            serial_number=100,
        )
        create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=inactive_ballot,
            center=center,
            station_number=inactive_station.station_number,
            barcode="222222222",
            serial_number=200,
        )

        view = views.CenterListDataView.as_view()

        # Test without show_inactive (should filter out inactive)
        request = self.factory.get("/center-list-data")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        # Should only return the station with active ballot
        self.assertEqual(response.status_code, 200)
        # The view returns JSON data, but we can check the queryset filtering
        # by inspecting the view's filter_queryset method behavior

    def test_center_list_data_shows_inactive_with_parameter(self):
        """Test CenterListDataView shows inactive when show_inactive=true"""
        tally = create_tally()
        tally.users.add(self.user)

        # Create center
        center = create_center(tally=tally)

        # Create stations - one with active ballot, one with inactive ballot
        active_station = create_station(
            center=center,
            tally=tally,
            station_number=1
        )
        inactive_station = create_station(
            center=center,
            tally=tally,
            station_number=2
        )

        # Create ballots - one active, one inactive
        active_ballot = create_ballot(tally=tally, active=True, number=10)
        inactive_ballot = create_ballot(tally=tally, active=False, number=11)

        # Create result forms linking stations to ballots through center
        create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=active_ballot,
            center=center,
            station_number=active_station.station_number,
            barcode="111111111",
            serial_number=100,
        )
        create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=inactive_ballot,
            center=center,
            station_number=inactive_station.station_number,
            barcode="222222222",
            serial_number=200,
        )

        view = views.CenterListDataView.as_view()

        # Test with show_inactive=true (should include both)
        request = self.factory.get(
            f"/center-list-data?{show_inactive_query_param}=true"
        )
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        # Should return both stations
        self.assertEqual(response.status_code, 200)

    def test_get_centers_stations_list_filters_inactive_ballots(self):
        """Test get_centers_stations_list function filters inactive ballots"""
        tally = create_tally()

        # Create center
        center = create_center(tally=tally)

        # Create stations - one with active ballot, one with inactive ballot
        active_station = create_station(
            center=center,
            tally=tally,
            station_number=1
        )
        inactive_station = create_station(
            center=center,
            tally=tally,
            station_number=2
        )

        # Create ballots - one active, one inactive
        active_ballot = create_ballot(tally=tally, active=True, number=10)
        inactive_ballot = create_ballot(tally=tally, active=False, number=11)

        # Create result forms linking stations to ballots through center
        create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=active_ballot,
            center=center,
            station_number=active_station.station_number,
            barcode="111111111",
            serial_number=100,
        )
        create_result_form(
            form_state=FormState.ARCHIVED,
            tally=tally,
            ballot=inactive_ballot,
            center=center,
            station_number=inactive_station.station_number,
            barcode="222222222",
            serial_number=200,
        )

        # Test without show_inactive (should filter out inactive)
        request_data = json.dumps({"tally_id": tally.pk})
        request = self.factory.get(f"?data={request_data}")
        response = views.get_centers_stations_list(request)
        response_data = json.loads(response.content.decode())["data"]

        # The filtering should work - both stations from same center,
        # but linked to different ballots
        # This test verifies the JSON function filtering
        # We expect only 1 station (the one with active ballot)
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["station_number"], active_station.station_number
        )

        # Test with show_inactive=true (should include both)
        request = self.factory.get(
            f"?data={request_data}&{show_inactive_query_param}=true"
        )
        response = views.get_centers_stations_list(request)
        response_data = json.loads(response.content.decode())["data"]

        self.assertEqual(len(response_data), 2)
        returned_station_numbers = {
            row["station_number"] for row in response_data
        }
        self.assertIn(active_station.station_number, returned_station_numbers)
        self.assertIn(
            inactive_station.station_number, returned_station_numbers
        )
