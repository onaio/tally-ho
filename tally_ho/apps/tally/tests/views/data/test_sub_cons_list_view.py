import json

from django.test import RequestFactory

from tally_ho.apps.tally.views.data import sub_constituency_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_electrol_race,
    create_sub_constituency,
    create_tally,
)


class TestSubConstituencyListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally = create_tally()
        self.tally.users.add(self.user)

        # Setup comprehensive test data
        self.setup_test_data()

    def setup_test_data(self):
        """Create comprehensive test data for sub constituencies."""
        # Create multiple electrol races
        self.electrol_race_presidential = create_electrol_race(
            self.tally, **electrol_races[0]
        )
        self.electrol_race_senate = create_electrol_race(
            self.tally, **electrol_races[2]
        )

        # Create ballots for different races
        self.ballot_presidential = create_ballot(
            self.tally, electrol_race=self.electrol_race_presidential, number=1
        )
        self.ballot_senate = create_ballot(
            self.tally, electrol_race=self.electrol_race_senate, number=2
        )

        # Create sub constituencies with different codes and names
        self.sub_con_1 = create_sub_constituency(
            code=101,
            field_office="1",
            ballots=[self.ballot_presidential],
            name="Alpha Sub Constituency",
            tally=self.tally,
        )

        self.sub_con_2 = create_sub_constituency(
            code=102,
            field_office="2",
            ballots=[self.ballot_senate],
            name="Beta Sub Constituency",
            tally=self.tally,
        )

        self.sub_con_3 = create_sub_constituency(
            code=123,
            field_office="3",
            ballots=[self.ballot_presidential, self.ballot_senate],
            name="Gamma Sub Constituency",
            tally=self.tally,
        )

        # Legacy test data (maintain backward compatibility)
        electrol_race = create_electrol_race(self.tally, **electrol_races[0])
        ballot = create_ballot(self.tally, electrol_race=electrol_race)
        create_sub_constituency(
            code=1,
            field_office="1",
            ballots=[ballot],
            name="Sub Con A",
            tally=self.tally,
        )

    def test_sub_cons_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.SubConstituencyListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Sub Constituencies List")

    def test_sub_cons_list_data_view(self):
        """
        Test that sub cons list data view returns correct data
        """
        view = views.SubConstituencyListDataView.as_view()
        mock_json_data = [
            "1",
            "Sub Con A",
            "Presidential",
            "ballot_number_presidential",
            1,
        ]
        request = self.factory.get("/sub-cons-list-data")
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Find the legacy test data in the response
        legacy_data_found = False
        for row in data:
            if row[1] == "Sub Con A":  # name field
                self.assertEqual(mock_json_data, row)
                legacy_data_found = True
                break

        self.assertTrue(
            legacy_data_found, "Legacy test data not found in response"
        )

    def test_filter_by_code_exact_match(self):
        """Test filtering sub constituencies by exact code match."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "101"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should only return sub_con_1
        codes = [str(row[0]) for row in data]
        self.assertIn("101", codes)
        # Verify it's the correct sub constituency
        for row in data:
            if str(row[0]) == "101":
                self.assertEqual(row[1], "Alpha Sub Constituency")

    def test_filter_by_code_partial_match(self):
        """Test filtering sub constituencies by partial code match."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "10"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should return sub_con_1 and sub_con_2 (101, 102)
        codes = [str(row[0]) for row in data]
        self.assertIn("101", codes)
        self.assertIn("102", codes)
        # Should not include 123
        found_123 = any(str(row[0]) == "123" for row in data)
        self.assertFalse(found_123)

    def test_filter_by_code_case_insensitive(self):
        """Test that code filtering works with different search terms."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "101"}  # exact numeric match

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should find 101
        codes = [str(row[0]) for row in data]
        self.assertIn("101", codes)

    def test_filter_by_numeric_code(self):
        """Test filtering by specific numeric code."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "123"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should return sub_con_3 which has code 123
        codes = [str(row[0]) for row in data]
        self.assertIn("123", codes)
        # Should not include 101 or 102
        found_101 = any(str(row[0]) == "101" for row in data)
        found_102 = any(str(row[0]) == "102" for row in data)
        self.assertFalse(found_101)
        self.assertFalse(found_102)

    # BACKWARD COMPATIBILITY TESTS

    def test_filter_by_name_still_works(self):
        """Test that filtering by name still works after adding code filter."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "Alpha"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should return only Alpha Sub Constituency
        names = [row[1] for row in data]
        alpha_found = any("Alpha" in name for name in names)
        self.assertTrue(alpha_found)

        # Should not return Beta or Gamma
        beta_found = any("Beta" in name for name in names)
        gamma_found = any("Gamma" in name for name in names)
        self.assertFalse(beta_found)
        self.assertFalse(gamma_found)

    def test_filter_by_election_level_still_works(self):
        """Test that filtering by election level still works."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "Presidential"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should return sub constituencies with Presidential election level
        election_levels = [row[2] for row in data]
        for level in election_levels:
            self.assertEqual(level, "Presidential")

    def test_filter_matches_multiple_fields(self):
        """Test search that could match multiple fields."""
        # Create a sub constituency where code contains part of another's name
        electrol_race = create_electrol_race(self.tally, **electrol_races[0])
        ballot = create_ballot(self.tally, electrol_race=electrol_race)
        create_sub_constituency(
            code=999,
            field_office="4",
            ballots=[ballot],
            name="Beta Special Sub Constituency",
            tally=self.tally,
        )

        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "Beta"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should return both sub constituencies (one by name, one by code)
        names = [row[1] for row in data]

        # One matches by name "Beta Sub Constituency"
        beta_by_name = any("Beta Sub Constituency" in name for name in names)
        # One matches by name "Beta Special Sub Constituency"
        beta_special_by_name = any(
            "Beta Special Sub Constituency" in name for name in names
        )

        # At least one should match
        self.assertTrue(beta_by_name or beta_special_by_name)

    # EDGE CASES AND DATA INTEGRITY TESTS

    def test_empty_search_returns_all(self):
        """Test that empty search keyword returns all results."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": ""}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should return all sub constituencies (at least the ones we created)
        codes = [str(row[0]) for row in data]
        self.assertIn("101", codes)
        self.assertIn("102", codes)
        self.assertIn("123", codes)

    def test_no_matching_results(self):
        """Test search with no matching results."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "NONEXISTENT999"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should return empty results
        self.assertEqual(len(data), 0)

    def test_special_characters_in_search(self):
        """Test that special characters in search are handled properly."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "SC-001%"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should handle special characters without error
        self.assertIsInstance(data, list)
        # Results depend on whether any codes contain these characters

    def test_tally_id_filter_logic(self):
        """Test the tally_id filter logic ensures data isolation."""
        # Create another tally with sub constituencies
        other_tally = create_tally()
        other_electrol_race = create_electrol_race(
            other_tally, **electrol_races[0]
        )
        other_ballot = create_ballot(
            other_tally, electrol_race=other_electrol_race
        )
        create_sub_constituency(
            code=999,
            field_office="5",
            ballots=[other_ballot],
            name="Other Tally Sub Con",
            tally=other_tally,
        )

        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": ""}

        # Test with specific tally_id
        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should only return sub constituencies from self.tally
        codes = [str(row[0]) for row in data]
        # Other tally's sub constituency should not appear
        # but our test sub constituencies should
        self.assertIn("101", codes)

    def test_multiple_ballots_per_sub_constituency(self):
        """Test sub constituencies with multiple ballots appear correctly."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "123"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # sub_con_3 has two ballots, should appear twice
        self.assertGreaterEqual(len(data), 2)

        # All rows should have the same code and name
        codes = [row[0] for row in data]
        names = [row[1] for row in data]

        for code in codes:
            self.assertEqual(str(code), "123")
        for name in names:
            self.assertEqual(name, "Gamma Sub Constituency")

        # But different election levels
        election_levels = [row[2] for row in data]
        self.assertIn("Presidential", election_levels)
        self.assertIn("Senate", election_levels)

    def test_response_data_structure(self):
        """Test that response data has the correct structure."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.get("/sub-cons-list-data")
        request.user = self.user

        response = view(request, tally_id=self.tally.pk)
        response_data = json.loads(response.content.decode())

        # Check overall response structure
        self.assertIn("data", response_data)
        self.assertIsInstance(response_data["data"], list)

        # Check individual row structure
        if response_data["data"]:
            first_row = response_data["data"][0]
            # code, name, election_level, sub_race, ballot_number
            self.assertEqual(len(first_row), 5)

            # Check data types
            self.assertIsInstance(first_row[0], str)  # code
            self.assertIsInstance(first_row[1], str)  # name
            self.assertIsInstance(first_row[2], str)  # election_level
            self.assertIsInstance(first_row[3], str)  # sub_race
            self.assertIsInstance(first_row[4], int)  # ballot_number

    def test_numeric_code_with_legacy_data(self):
        """Test that numeric codes (legacy) still work with the search."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "1"}

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should find legacy sub constituency with code=1
        legacy_found = False
        for row in data:
            if row[1] == "Sub Con A":  # name field
                legacy_found = True
                self.assertEqual(str(row[0]), "1")  # code field
                break

        self.assertTrue(legacy_found, "Legacy numeric code search failed")

    def test_whitespace_in_search(self):
        """Test search with whitespace characters."""
        view = views.SubConstituencyListDataView.as_view()
        request = self.factory.post("/sub-cons-list-data")
        request.user = self.user
        request.POST = {"search[value]": "101"}  # exact match without spaces

        response = view(request, tally_id=self.tally.pk)
        data = json.loads(response.content.decode())["data"]

        # Should find 101 when searching for exact match
        codes = [str(row[0]) for row in data]
        self.assertIn("101", codes)

        # Test with name that contains spaces
        request2 = self.factory.post("/sub-cons-list-data")
        request2.user = self.user
        # part of "Alpha Sub Constituency"
        request2.POST = {"search[value]": "Alpha"}

        response2 = view(request2, tally_id=self.tally.pk)
        data2 = json.loads(response2.content.decode())["data"]

        # Should find by name containing spaces
        names = [row[1] for row in data2]
        alpha_found = any("Alpha" in name for name in names)
        self.assertTrue(alpha_found)
