import json

from bs4 import BeautifulSoup
from django.test import RequestFactory

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.views.reports.turnout_reports_by_gender import (
    TurnoutReportByGenderAndAdminAreasDataView,
    TurnoutReportByGenderAndAdminAreasView,
)
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_candidate_result,
    create_constituency,
    create_electrol_race,
    create_office,
    create_reconciliation_form,
    create_region,
    create_result_form,
    create_station,
    create_sub_constituency,
    create_tally,
)


class TestTurnoutByGenderReport(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally, election_level="Municipal", ballot_name="Individual"
        )
        ballot = create_ballot(self.tally, electrol_race=self.electrol_race)
        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc = create_sub_constituency(
            code=1, field_office="1", ballots=[ballot], tally=self.tally
        )
        center, _ = Center.objects.get_or_create(
            code="1",
            mahalla="1",
            name="1",
            office=office,
            region=self.region.name,
            village="1",
            active=True,
            tally=self.tally,
            sub_constituency=self.sc,
            center_type=CenterType.GENERAL,
            constituency=self.constituency,
        )

        # Create stations with different genders
        self.station_male = create_station(
            center=center,
            registrants=100,
            tally=self.tally,
            station_number=1,
            gender=Gender.MALE,
        )
        self.station_female = create_station(
            center=center,
            registrants=120,
            tally=self.tally,
            station_number=2,
            gender=Gender.FEMALE,
        )

        # Create result forms for each station
        self.result_form_male = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station_male.station_number,
            ballot=ballot,
        )
        self.result_form_female = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station_female.station_number,
            ballot=ballot,
            serial_number=1,
            barcode="1234567890",
        )

        # Create reconciliation forms
        self.recon_form_male = create_reconciliation_form(
            result_form=self.result_form_male,
            user=self.user,
            number_valid_votes=55,
            number_invalid_votes=5,  # Invalid votes contribute to turnout
            number_ballots_received=100,
            entry_version=EntryVersion.FINAL,
        )
        self.recon_form_female = create_reconciliation_form(
            result_form=self.result_form_female,
            user=self.user,
            number_valid_votes=70,
            number_invalid_votes=10,  # Invalid votes contribute to turnout
            number_ballots_received=120,
            entry_version=EntryVersion.FINAL,
        )

        # Create candidates and results
        male_votes = 55
        create_candidate_result(
            self.result_form_male,
            votes=male_votes,
            user=self.user,
            tally=self.tally,
        )

        female_votes = 70
        create_candidate_result(
            self.result_form_female,
            votes=female_votes,
            user=self.user,
            tally=self.tally,
        )

    def test_turnout_report_by_gender_region_view(self):
        """
        Test the turnout report by gender for the region level
        """
        request = self.factory.get(
            f"/data/turnout-report-by-gender/{self.tally.pk}/region/"
        )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByGenderAndAdminAreasView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level="region")
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "html.parser")
        table_header_texts = [
            header.text for header in doc.find("thead").find_all("th")
        ]
        self.assertEqual(
            table_header_texts,
            [
                "Region",
                "Race Type",
                "Human",
                "Voters",
                "Registrants",
                "% Turnout",
            ],
        )

    def test_turnout_report_by_gender_office_view(self):
        """
        Test the turnout report by gender for the office level
        """
        request = self.factory.get(
            f"/data/turnout-report-by-gender/{self.tally.pk}/office/"
        )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByGenderAndAdminAreasView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level="office")
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "html.parser")
        table_header_texts = [
            header.text for header in doc.find("thead").find_all("th")
        ]
        self.assertEqual(
            table_header_texts,
            [
                "Office",
                "Race Type",
                "Human",
                "Voters",
                "Registrants",
                "% Turnout",
            ],
        )

    def test_turnout_report_by_gender_constituency_view(self):
        """
        Test the turnout report by gender for the constituency level
        """
        request = self.factory.get(
            f"/data/turnout-report-by-gender/{self.tally.pk}/constituency/"
        )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByGenderAndAdminAreasView.as_view()
        response = view(
            request, tally_id=self.tally.pk, admin_level="constituency"
        )
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "html.parser")
        table_header_texts = [
            header.text for header in doc.find("thead").find_all("th")
        ]
        self.assertEqual(
            table_header_texts,
            [
                "Main-Constituency",
                "Race Type",
                "Human",
                "Voters",
                "Registrants",
                "% Turnout",
            ],
        )

    def test_turnout_report_by_gender_sub_constituency_view(self):
        """
        Test the turnout report by gender for the sub constituency level
        """
        request = self.factory.get(
            f"/data/turnout-report-by-gender/{self.tally.pk}/sub_constituency/"
        )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByGenderAndAdminAreasView.as_view()
        response = view(
            request, tally_id=self.tally.pk, admin_level="sub_constituency"
        )
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)

        doc = BeautifulSoup(content, "html.parser")
        table_header_texts = [
            header.text for header in doc.find("thead").find_all("th")
        ]
        self.assertEqual(
            table_header_texts,
            [
                "Municipality",
                "Race Type",
                "Human",
                "Voters",
                "Registrants",
                "% Turnout",
            ],
        )

    def test_turnout_data_by_gender_region_view(self):
        """
        Test the turnout data by gender for the region level
        """
        request = self.factory.get(
            f"/data/turnout-report-by-gender-data/{self.tally.pk}/region/"
        )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByGenderAndAdminAreasDataView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level="region")
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 200)

        # Sort by gender column
        data = sorted(content.get("data"), key=lambda x: x[2])

        # Expecting two rows, one for Male, one for Female
        self.assertEqual(len(data), 2)

        # Male Row Data Check
        # Male should be first after sorting
        (
            area_name_male,
            sub_race_male,
            gender_male,
            voters_male,
            registrants_male,
            turnout_male,
        ) = data[0]
        self.assertEqual(area_name_male, '<td class="center">Region</td>')
        self.assertEqual(sub_race_male, '<td class="center">Individual</td>')
        self.assertEqual(gender_male, '<td class="center">Man</td>')
        self.assertEqual(
            voters_male, '<td class="center">60</td>'
        )  # 55 valid + 5 invalid
        self.assertEqual(registrants_male, '<td class="center">100</td>')
        self.assertEqual(turnout_male, '<td class="center">60.0</td>')

        # Female Row Data Check
        (
            area_name_female,
            sub_race_female,
            gender_female,
            voters_female,
            registrants_female,
            turnout_female,
        ) = data[1]  # Female should be second
        self.assertEqual(area_name_female, '<td class="center">Region</td>')
        self.assertEqual(sub_race_female, '<td class="center">Individual</td>')
        self.assertEqual(gender_female, '<td class="center">Woman</td>')
        # 70 valid + 10 invalid
        self.assertEqual(voters_female, '<td class="center">80</td>')
        self.assertEqual(registrants_female, '<td class="center">120</td>')
        # 80 / 120 * 100
        self.assertEqual(turnout_female, '<td class="center">66.67</td>')

        # Aggregate Data Check
        (
            agg_area,
            agg_sub_race,
            agg_gender,
            agg_voters,
            agg_registrants,
            agg_turnout,
        ) = content.get("aggregate")[0]

        self.assertEqual(agg_area, '<td class="center">Total</td>')
        self.assertEqual(agg_sub_race, '<td class="center"></td>')
        self.assertEqual(agg_gender, '<td class="center"></td>')
        # 60 + 80
        self.assertEqual(agg_voters, '<td class="center">140</td>')
        # 100 + 120
        self.assertEqual(agg_registrants, '<td class="center">220</td>')
        # 140 / 220 * 100
        self.assertEqual(agg_turnout, '<td class="center">63.64</td>')

    def test_turnout_data_by_gender_office_view(self):
        """
        Test the turnout data by gender for the office level
        """
        request = self.factory.get(
            f"/data/turnout-report-by-gender-data/{self.tally.pk}/office/"
        )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByGenderAndAdminAreasDataView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level="office")
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 200)

        # Sort by gender column
        data = sorted(content.get("data"), key=lambda x: x[2])

        # Male Row Data Check
        (
            area_name_male,
            _,
            gender_male,
            voters_male,
            registrants_male,
            turnout_male,
        ) = data[0]
        self.assertEqual(area_name_male, '<td class="center">office</td>')
        self.assertEqual(gender_male, '<td class="center">Man</td>')
        self.assertEqual(voters_male, '<td class="center">60</td>')
        self.assertEqual(registrants_male, '<td class="center">100</td>')
        self.assertEqual(turnout_male, '<td class="center">60.0</td>')

        # Female Row Data Check
        (
            area_name_female,
            _,
            gender_female,
            voters_female,
            registrants_female,
            turnout_female,
        ) = data[1]
        self.assertEqual(area_name_female, '<td class="center">office</td>')
        self.assertEqual(gender_female, '<td class="center">Woman</td>')
        self.assertEqual(voters_female, '<td class="center">80</td>')
        self.assertEqual(registrants_female, '<td class="center">120</td>')
        self.assertEqual(turnout_female, '<td class="center">66.67</td>')

        # Aggregate Data Check (should be same as region level in this setup)
        (_, _, _, agg_voters, agg_registrants, agg_turnout) = content.get(
            "aggregate"
        )[0]
        self.assertEqual(agg_voters, '<td class="center">140</td>')
        self.assertEqual(agg_registrants, '<td class="center">220</td>')
        self.assertEqual(agg_turnout, '<td class="center">63.64</td>')

    def test_turnout_data_by_gender_sub_constituency_view(self):
        """
        Test the turnout data by gender for the sub constituency level
        """
        request = self.factory.get(
            str(
                f"/data/turnout-report-by-gender-data/"
                f"{self.tally.pk}/sub_constituency/"
            )
        )
        request.user = self.user
        request.session = {}
        view = TurnoutReportByGenderAndAdminAreasDataView.as_view()
        response = view(
            request, tally_id=self.tally.pk, admin_level="sub_constituency"
        )
        content = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 200)

        # Sort by gender column
        data = sorted(content.get("data"), key=lambda x: x[2])

        # Male Row Data Check
        (
            area_name_male,
            _,
            gender_male,
            voters_male,
            registrants_male,
            turnout_male,
        ) = data[0]
        self.assertEqual(
            area_name_male, f'<td class="center">{self.sc.name}</td>'
        )  # Sub Constituency Code
        self.assertEqual(gender_male, '<td class="center">Man</td>')
        self.assertEqual(voters_male, '<td class="center">60</td>')
        self.assertEqual(registrants_male, '<td class="center">100</td>')
        self.assertEqual(turnout_male, '<td class="center">60.0</td>')

        # Female Row Data Check
        (
            area_name_female,
            _,
            gender_female,
            voters_female,
            registrants_female,
            turnout_female,
        ) = data[1]
        self.assertEqual(
            area_name_female, f'<td class="center">{self.sc.name}</td>'
        )  # Sub Constituency Code
        self.assertEqual(gender_female, '<td class="center">Woman</td>')
        self.assertEqual(voters_female, '<td class="center">80</td>')
        self.assertEqual(registrants_female, '<td class="center">120</td>')
        self.assertEqual(turnout_female, '<td class="center">66.67</td>')

        # Aggregate Data Check (should be same as region level in this setup)
        (_, _, _, agg_voters, agg_registrants, agg_turnout) = content.get(
            "aggregate"
        )[0]
        self.assertEqual(agg_voters, '<td class="center">140</td>')
        self.assertEqual(agg_registrants, '<td class="center">220</td>')
        self.assertEqual(agg_turnout, '<td class="center">63.64</td>')
