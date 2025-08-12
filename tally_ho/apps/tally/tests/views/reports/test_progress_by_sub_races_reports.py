import json

from django.test import RequestFactory

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.views.reports import (
    progress_by_sub_races_reports as progress_reports,
)
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_ballot,
    create_candidates,
    create_constituency,
    create_electrol_race,
    create_office,
    create_reconciliation_form,
    create_region,
    create_result,
    create_result_form,
    create_station,
    create_sub_constituency,
    create_tally,
)


class TestSubRacesReports(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally, **electrol_races[0]
        )
        ballot = create_ballot(self.tally, electrol_race=self.electrol_race)
        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc = create_sub_constituency(
            code=1, tally=self.tally, field_office="1", ballots=[ballot]
        )
        center, _ = Center.objects.get_or_create(
            code="1",
            mahalla="1",
            name="1",
            office=office,
            region="1",
            village="1",
            active=True,
            tally=self.tally,
            sub_constituency=self.sc,
            center_type=CenterType.GENERAL,
            constituency=self.constituency,
        )
        self.station = create_station(
            center=center, registrants=20, tally=self.tally
        )
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station.station_number,
            ballot=ballot,
        )
        self.recon_form = create_reconciliation_form(
            result_form=self.result_form,
            user=self.user,
            number_valid_votes=20,
            number_invalid_votes=0,
            number_of_voters=20,
        )
        votes = 20
        create_candidates(
            self.result_form,
            votes=votes,
            user=self.user,
            num_results=1,
            tally=self.tally,
        )
        for result in self.result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(self.result_form, result.candidate, self.user, votes)

    def test_progress_reports_view(self):
        """
        Test that the progress views returns the correct progress reports.
        """
        # Regions
        view = progress_reports.RegionsReportView.as_view()
        request = self.factory.get("/data/progress-report-list/1")
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk,
        )
        data = json.loads(response.content.decode())["data"]
        ballot_name = electrol_races[0]["ballot_name"]
        ballot_name_percentage = f"{ballot_name}_percentage"
        keys = [
            ballot_name,
            ballot_name_percentage,
            "overall",
            "overall_percentage",
        ]
        for data_item in data:
            for key in keys:
                self.assertIn(key, data_item)
        # totals
        totals_row = data[-1]
        self.assertEqual("Total", totals_row["region_name"])
        ballot_record_total = 0
        for data_item in data[:-1]:
            ballot_record_total += int(data_item[ballot_name].split("/")[0])

        self.assertEqual(
            int(data[-1][ballot_name].split("/")[0]), ballot_record_total
        )

        # Offices
        view = progress_reports.OfficesReportView.as_view()
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk,
        )
        data = json.loads(response.content.decode())["data"]
        ballot_name = electrol_races[0]["ballot_name"]
        ballot_name_percentage = f"{ballot_name}_percentage"
        keys = [
            ballot_name,
            ballot_name_percentage,
            "overall",
            "overall_percentage",
        ]
        for data_item in data:
            for key in keys:
                self.assertIn(key, data_item)
        # totals
        totals_row = data[-1]
        self.assertEqual("Total", totals_row["office_name"])
        ballot_record_total = 0
        for data_item in data[:-1]:
            ballot_record_total += int(data_item[ballot_name].split("/")[0])

        self.assertEqual(
            int(data[-1][ballot_name].split("/")[0]), ballot_record_total
        )

        # Constituencies
        view = progress_reports.ConstituenciesReportView.as_view()
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk,
        )
        data = json.loads(response.content.decode())["data"]
        ballot_name = electrol_races[0]["ballot_name"]
        ballot_name_percentage = f"{ballot_name}_percentage"
        keys = [
            ballot_name,
            ballot_name_percentage,
            "overall",
            "overall_percentage",
        ]
        for data_item in data:
            for key in keys:
                self.assertIn(key, data_item)
        # totals
        totals_row = data[-1]
        self.assertEqual("Total", totals_row["constituency_name"])
        ballot_record_total = 0
        for data_item in data[:-1]:
            ballot_record_total += int(data_item[ballot_name].split("/")[0])

        self.assertEqual(
            int(data[-1][ballot_name].split("/")[0]), ballot_record_total
        )

        # Sub Constituencies
        view = progress_reports.SubConstituenciesReportView.as_view()
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk,
        )
        data = json.loads(response.content.decode())["data"]
        ballot_name = electrol_races[0]["ballot_name"]
        ballot_name_percentage = f"{ballot_name}_percentage"
        keys = [
            ballot_name,
            ballot_name_percentage,
            "overall",
            "overall_percentage",
        ]
        for data_item in data:
            for key in keys:
                self.assertIn(key, data_item)
        # totals
        totals_row = data[-1]
        self.assertEqual("Total", totals_row["sub_constituency_code"])
        ballot_record_total = 0
        for data_item in data[:-1]:
            ballot_record_total += int(data_item[ballot_name].split("/")[0])
        self.assertEqual(
            int(data[-1][ballot_name].split("/")[0]), ballot_record_total
        )

        # progress_report
        view = progress_reports.progress_report
        request = self.factory.get("/data/progress-report-list/")
        request.user = self.user
        request.session = {"locale": "en"}
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)
