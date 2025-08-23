import datetime
import json

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory

from tally_ho.apps.tally.views.constants import (election_level_query_param,
                                                 pending_at_state_query_param,
                                                 show_inactive_query_param,
                                                 sub_con_code_query_param,
                                                 sub_race_query_param)
from tally_ho.apps.tally.views.data import form_list_view as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_center, create_electrol_race,
                                           create_result_form,
                                           create_result_forms_per_form_state,
                                           create_station,
                                           create_sub_constituency,
                                           create_tally)


class TestFormListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally, **electrol_races[0]
        )

    def test_access_control(self):
        view = views.FormListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)

        request.user = AnonymousUser()
        request.session = {}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)

    def test_form_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Form List")
        self.assertContains(response, "New Form")

    def test_csv_export(self):
        ballot = create_ballot(self.tally, self.electrol_race)
        sub_con = create_sub_constituency(code=12345, tally=self.tally)
        center_code = "12345"
        center = create_center(
            center_code, tally=self.tally, sub_constituency=sub_con
        )
        station = create_station(center)
        state = "unsubmitted"
        form_state = FormState[state.upper()]
        barcode = f"{center_code}0{station.station_number}011"
        result_form = create_result_form(
            ballot=ballot,
            barcode=barcode,
            form_state=form_state,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )
        view = views.FormListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk, state=state)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn(result_form.barcode, content)
        formatted_datestring = datetime.date.today().strftime("%Y%m%d")
        filename = f"{state}_form_list_{formatted_datestring}.csv"
        self.assertIn(filename, response.headers["Content-Disposition"])

    def test_form_not_received_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Forms Not Received")
        self.assertNotContains(response, "New Form")

    def test_form_not_received_list_csv_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, format="csv", tally_id=tally.pk)
        self.assertContains(response, "barcode")

    def test_forms_for_race(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        view = views.FormsForRaceView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, ballot=ballot.number, tally_id=tally.pk)
        self.assertContains(response, "Forms for Race %s" % ballot.number)
        self.assertNotContains(response, "New Form")

    def test_form_list_view_filter_on_query_params(self):
        """
        #369 - check that filter search params are passed on
        to data view. and data view uses the query params to
        filter
        """
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        view = views.FormListView.as_view()
        data_view = views.FormListDataView.as_view()
        request = self.factory.get(
            f"/1/?{pending_at_state_query_param}=data_entry_1"
            f"&{election_level_query_param}=HoR"
            f"&{sub_race_query_param}=ballot_number_HOR_women"
            f"&{sub_con_code_query_param}=12345"
        )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)
        raw_data_response_for_electrol_race_hor = data_view(
            request, tally_id=self.tally.pk
        ).content

        self.assertEqual(
            response.context_data["remote_url"],
            f"/data/form-list-data/{self.tally.pk}/?"
            "pending_at_form_state=data_entry_1"
            f"&{election_level_query_param}=HoR"
            f"&{sub_race_query_param}=ballot_number_HOR_women"
            "&sub_con_code=12345",
        )
        self.assertListEqual(response.template_name, ["data/forms.html"])

        data_response_for_electrol_race_hor = json.loads(
            raw_data_response_for_electrol_race_hor
        ).get("data")
        self.assertListEqual(data_response_for_electrol_race_hor, [])

        request = self.factory.get(
            f"/1/?{pending_at_state_query_param}="
            f"data_entry_1"
            f"&{election_level_query_param}="
            f"{self.electrol_race.election_level}"
            f"&{sub_race_query_param}={self.electrol_race.ballot_name}"
            f"&{sub_con_code_query_param}=12345"
        )
        request.user = self.user
        request.session = {}

        raw_data_response_for_electrol_race_presidential = data_view(
            request, tally_id=self.tally.pk
        ).content
        data_response_for_electrol_race_presidential = json.loads(
            raw_data_response_for_electrol_race_presidential
        ).get("data")
        self.assertEqual(len(data_response_for_electrol_race_presidential), 4)
        election_levels_in_response = [
            form[9] for form in data_response_for_electrol_race_presidential
        ]
        sub_races_in_response = [
            form[10] for form in data_response_for_electrol_race_presidential
        ]
        form_states_in_response = [
            form[12] for form in data_response_for_electrol_race_presidential
        ]

        self.assertListEqual(
            election_levels_in_response,
            ["Presidential", "Presidential", "Presidential", "Presidential"],
        )
        self.assertListEqual(
            sub_races_in_response,
            [
                "ballot_number_presidential",
                "ballot_number_presidential",
                "ballot_number_presidential",
                "ballot_number_presidential",
            ],
        )
        expected_form_states = ["Audit", "Clearance", "Intake", "Unsubmitted"]
        for state in expected_form_states:
            self.assertIn(state, form_states_in_response)

    def test_active_ballot_filtering(self):
        """
        Test that FormListDataView only returns forms for active ballots
        """

        # Create an active ballot
        active_ballot = create_ballot(
            self.tally, self.electrol_race, active=True, number=101
        )

        # Create an inactive ballot
        inactive_ballot = create_ballot(
            self.tally, self.electrol_race, active=False, number=102
        )

        # Create result forms for both ballots
        sub_con = create_sub_constituency(code=5432, tally=self.tally)
        center = create_center(
            "5432", tally=self.tally, sub_constituency=sub_con
        )
        station = create_station(center)

        active_form = create_result_form(
            ballot=active_ballot,
            barcode="543200101",
            serial_number=54320001,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        inactive_form = create_result_form(
            ballot=inactive_ballot,
            barcode="543200102",
            serial_number=54320002,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        # Test main queryset filtering
        data_view = views.FormListDataView.as_view()
        request = self.factory.post("/")
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        # Should only contain the form from the active ballot
        test_barcodes = [active_form.barcode, inactive_form.barcode]
        test_data = [
            row for row in data if row[0] in test_barcodes
        ]  # barcode is at index 0

        self.assertEqual(len(test_data), 1)
        returned_barcode = test_data[0][0]  # barcode is at index 0
        self.assertEqual(returned_barcode, active_form.barcode)

        # Test election level/sub-race filtering with active ballot check
        request = self.factory.post(
            f"/?{election_level_query_param}={self.electrol_race.election_level}"
            f"&{sub_race_query_param}={self.electrol_race.ballot_name}"
        )
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        # Should still only contain the form from the active ballot
        # Filter data to only forms we created for this test
        test_data = [
            row for row in data if row[0] in test_barcodes
        ]  # barcode is at index 0

        self.assertEqual(len(test_data), 1)
        returned_barcode = test_data[0][0]  # barcode is at index 0
        self.assertEqual(returned_barcode, active_form.barcode)

        # Test ballot number filtering with active ballot check
        # Should raise Http404 when filtering by inactive ballot number
        request = self.factory.post(
            "/", {"ballot[value]": str(inactive_ballot.number)}
        )
        request.user = self.user
        request.session = {}

        with self.assertRaises(Http404):
            data_view(request, tally_id=self.tally.pk)

        # Test with active ballot number should work
        request = self.factory.post(
            "/", {"ballot[value]": str(active_ballot.number)}
        )
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        # Should find the form from the active ballot
        test_data = [
            row for row in data if row[0] in test_barcodes
        ]  # barcode is at index 0
        self.assertEqual(len(test_data), 1)
        self.assertEqual(test_data[0][0], active_form.barcode)

    def test_show_inactive_parameter_default_behavior(self):
        """
        Test that by default (show_inactive not set or false),
        only active ballots are shown
        """
        # Create an active ballot
        active_ballot = create_ballot(
            self.tally, self.electrol_race, active=True, number=201
        )

        # Create an inactive ballot
        inactive_ballot = create_ballot(
            self.tally, self.electrol_race, active=False, number=202
        )

        # Create result forms for both ballots
        sub_con = create_sub_constituency(code=6543, tally=self.tally)
        center = create_center(
            "6543", tally=self.tally, sub_constituency=sub_con
        )
        station = create_station(center)

        active_form = create_result_form(
            ballot=active_ballot,
            barcode="654300201",
            serial_number=65430001,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        inactive_form = create_result_form(
            ballot=inactive_ballot,
            barcode="654300202",
            serial_number=65430002,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        data_view = views.FormListDataView.as_view()

        # Test without show_inactive parameter (default behavior)
        request = self.factory.post("/")
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        test_barcodes = [active_form.barcode, inactive_form.barcode]
        test_data = [row for row in data if row[0] in test_barcodes]

        # Should only contain the active ballot's form
        self.assertEqual(len(test_data), 1)
        self.assertEqual(test_data[0][0], active_form.barcode)

        # Test with show_inactive=false explicitly
        request = self.factory.post(f"/?{show_inactive_query_param}=false")
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        test_data = [row for row in data if row[0] in test_barcodes]

        # Should still only contain the active ballot's form
        self.assertEqual(len(test_data), 1)
        self.assertEqual(test_data[0][0], active_form.barcode)

    def test_show_inactive_parameter_true(self):
        """
        Test that when show_inactive=true, both active and inactive
        ballots are shown
        """
        # Create an active ballot
        active_ballot = create_ballot(
            self.tally, self.electrol_race, active=True, number=301
        )

        # Create an inactive ballot
        inactive_ballot = create_ballot(
            self.tally, self.electrol_race, active=False, number=302
        )

        # Create result forms for both ballots
        sub_con = create_sub_constituency(code=7654, tally=self.tally)
        center = create_center(
            "7654", tally=self.tally, sub_constituency=sub_con
        )
        station = create_station(center)

        active_form = create_result_form(
            ballot=active_ballot,
            barcode="765400301",
            serial_number=76540001,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        inactive_form = create_result_form(
            ballot=inactive_ballot,
            barcode="765400302",
            serial_number=76540002,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        data_view = views.FormListDataView.as_view()

        # Test with show_inactive=true
        request = self.factory.post(f"/?{show_inactive_query_param}=true")
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        test_barcodes = [active_form.barcode, inactive_form.barcode]
        test_data = [row for row in data if row[0] in test_barcodes]

        # Should contain both forms
        self.assertEqual(len(test_data), 2)
        returned_barcodes = {row[0] for row in test_data}
        self.assertIn(active_form.barcode, returned_barcodes)
        self.assertIn(inactive_form.barcode, returned_barcodes)

    def test_show_inactive_parameter_with_election_level_filter(self):
        """
        Test that show_inactive parameter works correctly with election
        level filtering
        """
        # Create an active ballot
        active_ballot = create_ballot(
            self.tally, self.electrol_race, active=True, number=401
        )

        # Create an inactive ballot
        inactive_ballot = create_ballot(
            self.tally, self.electrol_race, active=False, number=402
        )

        # Create result forms for both ballots
        sub_con = create_sub_constituency(code=8765, tally=self.tally)
        center = create_center(
            "8765", tally=self.tally, sub_constituency=sub_con
        )
        station = create_station(center)

        active_form = create_result_form(
            ballot=active_ballot,
            barcode="876500401",
            serial_number=87650001,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        inactive_form = create_result_form(
            ballot=inactive_ballot,
            barcode="876500402",
            serial_number=87650002,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        data_view = views.FormListDataView.as_view()

        # Test with show_inactive=true and election level filter
        request = self.factory.post(
            f"/?{show_inactive_query_param}=true"
            f"&{election_level_query_param}={self.electrol_race.election_level}"
            f"&{sub_race_query_param}={self.electrol_race.ballot_name}"
        )
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        test_barcodes = [active_form.barcode, inactive_form.barcode]
        test_data = [row for row in data if row[0] in test_barcodes]

        # Should contain both forms when showing inactive
        self.assertEqual(len(test_data), 2)
        returned_barcodes = {row[0] for row in test_data}
        self.assertIn(active_form.barcode, returned_barcodes)
        self.assertIn(inactive_form.barcode, returned_barcodes)

    def test_show_inactive_parameter_with_ballot_filter(self):
        """
        Test that show_inactive parameter works correctly with ballot
        number filtering
        """
        # Create an inactive ballot
        inactive_ballot = create_ballot(
            self.tally, self.electrol_race, active=False, number=501
        )

        # Create result form for inactive ballot
        sub_con = create_sub_constituency(code=9876, tally=self.tally)
        center = create_center(
            "9876", tally=self.tally, sub_constituency=sub_con
        )
        station = create_station(center)

        inactive_form = create_result_form(
            ballot=inactive_ballot,
            barcode="987600501",
            serial_number=98760001,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        data_view = views.FormListDataView.as_view()

        # Test filtering by inactive ballot number without show_inactive
        # Should raise Http404
        request = self.factory.post(
            "/", {"ballot[value]": str(inactive_ballot.number)}
        )
        request.user = self.user
        request.session = {}

        with self.assertRaises(Http404):
            data_view(request, tally_id=self.tally.pk)

        # Test filtering by inactive ballot number with show_inactive=true
        # Should work and return the form
        request = self.factory.post(
            f"/?{show_inactive_query_param}=true",
            {"ballot[value]": str(inactive_ballot.number)}
        )
        request.user = self.user
        request.session = {}

        response = data_view(request, tally_id=self.tally.pk)
        data = json.loads(response.content).get("data")

        test_data = [row for row in data if row[0] == inactive_form.barcode]
        self.assertEqual(len(test_data), 1)
        self.assertEqual(test_data[0][0], inactive_form.barcode)

    def test_csv_export_with_show_inactive(self):
        """
        Test that CSV export respects the show_inactive parameter
        """
        # Create an active ballot
        active_ballot = create_ballot(
            self.tally, self.electrol_race, active=True, number=601
        )

        # Create an inactive ballot
        inactive_ballot = create_ballot(
            self.tally, self.electrol_race, active=False, number=602
        )

        # Create result forms for both ballots
        sub_con = create_sub_constituency(code=1987, tally=self.tally)
        center = create_center(
            "1987", tally=self.tally, sub_constituency=sub_con
        )
        station = create_station(center)

        active_form = create_result_form(
            ballot=active_ballot,
            barcode="198700601",
            serial_number=19870001,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        inactive_form = create_result_form(
            ballot=inactive_ballot,
            barcode="198700602",
            serial_number=19870002,
            form_state=FormState.UNSUBMITTED,
            center=center,
            station_number=station.station_number,
            tally=self.tally,
        )

        view = views.FormListView.as_view()

        # Test CSV export without show_inactive (should only include active)
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk, state="__all__")

        self.assertEqual(response["Content-Type"], "text/csv")
        content = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn(active_form.barcode, content)
        self.assertNotIn(inactive_form.barcode, content)

        # Test CSV export with show_inactive=true (should include both)
        request = self.factory.get(f"/?{show_inactive_query_param}=true")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=self.tally.pk, state="__all__")

        self.assertEqual(response["Content-Type"], "text/csv")
        content = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn(active_form.barcode, content)
        self.assertIn(inactive_form.barcode, content)
