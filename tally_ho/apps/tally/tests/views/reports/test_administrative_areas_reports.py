import json

from django.test import RequestFactory
from django.urls import reverse

from tally_ho.apps.tally.models import Station
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.views.reports import \
    administrative_areas_reports as admin_reports
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_candidates, create_clearance,
                                           create_constituency,
                                           create_electrol_race, create_office,
                                           create_reconciliation_form,
                                           create_region, create_result,
                                           create_result_form, create_station,
                                           create_sub_constituency,
                                           create_tally)


class TestAdministrativeAreasReports(TestBase):
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
            code=1, field_office="1", ballots=[ballot]
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

    def test_sub_constituency_turn_out_and_votes_summary_reports(self):
        """
        Test that the sub constituency turn out and votes summary reports are
        rendered as expected.
        """
        # add
        view = admin_reports.SummaryReportDataView.as_view()
        request = self.factory.post("/sub-constituency-summary-report")
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk,
        )

        # Sub Constituency votes summary report tests
        code, valid_votes, invalid_votes, _, _, _ = (
            json.loads(response.content.decode())["data"][0]
        )

        self.assertEqual(
            code, '<td class="center">{}</td>'.format(self.sc.code)
        )
        self.assertEqual(
            valid_votes,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_valid_votes
            ),
        )
        self.assertEqual(
            invalid_votes,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_invalid_votes
            ),
        )

        view = admin_reports.ProgressiveReportDataView.as_view()
        request = self.factory.get("/sub-cons-progressive-report-list")
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk,
        )
        candidates_count = Candidate.objects.filter(
            tally__id=self.tally.pk
        ).count()

        # Sub Constituency progressive report tests
        code, num_candidates, num_votes, _, _, _ = json.loads(
            response.content.decode()
        )["data"][0]

        self.assertEqual(
            code, '<td class="center">{}</td>'.format(self.sc.code)
        )
        self.assertEqual(
            num_votes,
            '<td class="center">{}</td>'.format(self.result_form.num_votes),
        )
        self.assertEqual(
            num_candidates,
            '<td class="center">{}</td>'.format(candidates_count),
        )

    def apply_filter(self, data):
        view = admin_reports.ResultFormResultsListDataView.as_view()
        request = self.factory.post("/form-results", data=data)
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
        )
        return response

    def test_result_form_result_list_data_view_filters(self):
        """
        Test ResultFormResultsListDataView filters
        """
        # test race type filter
        data = {
            "data": str(
                {
                    "election_level_names": ["Presidential"],
                    "sub_race_type_names": [
                        "ballot_number_presidential_runoff"
                    ],
                }
            )
        }
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 0)
        data = {
            "data": str(
                {
                    "election_level_names": ["Presidential"],
                    "sub_race_type_names": ["ballot_number_presidential"],
                }
            )
        }
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)

        # test center filter
        data = {"data": '{"select_1_ids": ["-1"]}'}  # non existent id
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 0)
        center_id = self.station.center.id
        data = {"data": '{"select_1_ids": ' + f'["{center_id}"]' + "}"}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)

        # test stations filter
        data = {"data": '{"select_2_ids": ["-1"]}'}  # non existent id
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 0)
        station_id = self.station.id
        data = {"data": '{"select_2_ids": ' + f'["{station_id}"]' + "}"}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)

        # test ballot status filter
        data = {"data": '{"ballot_status": ["not_available_for_release"]}'}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)
        data = {"data": '{"ballot_status": ["available_for_release"]}'}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 0)

        # test station filter
        data = {"data": '{"station_status": ["active"]}'}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)
        data = {"data": '{"station_status": ["inactive"]}'}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 0)

        # test candidate status
        data = {"data": '{"candidate_status": ["active"]}'}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)
        data = {"data": '{"candidate_status": ["inactive"]}'}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 0)

        # test station percentage processed
        data = {"data": '{"percentage_processed": "10"}'}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)

        # test sub constituency filter
        data = {"data": '{"sub_con_codes": ' + f'["{self.sc.code}"]' + "}"}
        response = self.apply_filter(data)
        self.assertEqual(len(json.loads(response.content.decode())["data"]), 2)

    def test_administrative_areas_reports_views(self):
        # test ActiveCandidatesVotesListView
        tally = create_tally()
        view = admin_reports.ActiveCandidatesVotesListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

        # test ActiveCandidatesVotesDataView
        view = admin_reports.ActiveCandidatesVotesDataView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        request = self.factory.post("/")
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

        # test AllCandidatesVotesListView
        view = admin_reports.AllCandidatesVotesListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

        # test AllCandidatesVotesDataView
        view = admin_reports.AllCandidatesVotesDataView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        request = self.factory.post("/")
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

        # test DuplicateResultsListView
        view = admin_reports.DuplicateResultsListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

        # test DuplicateResultsListDataView
        view = admin_reports.DuplicateResultsListDataView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        request = self.factory.post("/")
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

        # test ResultFormResultsListView
        view = admin_reports.ResultFormResultsListView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        report_types = admin_reports.report_types.values()

        # test SubConstituencyReportsView
        view = admin_reports.SubConstituencyReportsView.as_view(
            template_name="test.html"
        )
        for report_type in report_types:
            response = view(
                request,
                tally_id=self.tally.id,
                region_id=self.region.id,
                constituency_id=self.constituency.id,
                sub_constituency_id=self.sc.id,
                report_type=report_type,
            )
            self.assertEqual(response.status_code, 200)

        # test ConstituencyReportsView
        view = admin_reports.ConstituencyReportsView.as_view(
            template_name="test.html"
        )
        for report_type in report_types:
            response = view(
                request,
                tally_id=self.tally.id,
                region_id=self.region.id,
                constituency_id=self.constituency.id,
                report_type=report_type,
            )
            self.assertEqual(response.status_code, 200)
        # test RegionsReportsView
        view = admin_reports.RegionsReportsView.as_view(
            template_name="test.html"
        )
        for report_type in report_types:
            response = view(
                request,
                tally_id=self.tally.id,
                region_id=self.region.id,
                report_type=report_type,
            )
            self.assertEqual(response.status_code, 200)

        # test ProgressiveReportView
        view = admin_reports.ProgressiveReportView.as_view(
            template_name="test.html"
        )
        response = view(
            request,
            tally_id=self.tally.id,
            region_id=self.region.id,
        )
        self.assertEqual(response.status_code, 200)

        # test DiscrepancyReportView
        discrepancy_reports = [
            "stations-and-centers-under-process-audit-list",
            "stations-and-centers-under-investigation-list",
            "stations-and-centers-excluded-after-investigation-list",
        ]
        view = admin_reports.DiscrepancyReportView.as_view(
            template_name="reports/administrative_areas_reports.html"
        )
        for report in discrepancy_reports:
            response = view(
                request,
                tally_id=self.tally.id,
                region_id=self.region.id,
                constituency_id=self.constituency.id,
                report_name=report,
            )
            self.assertEqual(response.status_code, 200)
        # test DiscrepancyReportDataView
        view = admin_reports.DiscrepancyReportDataView.as_view(
            template_name="test.html"
        )
        for report in discrepancy_reports:
            response = view(
                request,
                tally_id=self.tally.id,
                region_id=self.region.id,
                constituency_id=self.constituency.id,
                report_name=report,
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                json.loads(response.content.decode())["recordsTotal"], 1
            )
        # test SummaryReportView
        view = admin_reports.SummaryReportView.as_view(
            template_name="test.html"
        )
        response = view(
            request,
            tally_id=self.tally.id,
            region_id=self.region.id,
            constituency_id=self.constituency.id,
        )
        self.assertEqual(response.status_code, 200)

    def test_get_stations_and_centers_by_admin_area(self):
        discrepancy_reports = [
            "stations-and-centers-under-process-audit-list",
            "stations-and-centers-under-investigation-list",
            "stations-and-centers-excluded-after-investigation-list",
        ]
        for report in discrepancy_reports:
            qs = admin_reports.get_stations_and_centers_by_admin_area(
                self.tally.id,
                "id",
                report,
                self.region.id,
                self.constituency.id,
            )
            self.assertEqual(qs.count(), 0)

        # test get_admin_areas_with_forms_in_audit
        qs = admin_reports.get_admin_areas_with_forms_in_audit(
            self.tally.id, "id", self.region.id, self.constituency.id
        )
        self.assertEqual(qs.count(), 0)

    def test_export_results_queryset(self):
        qs = Result.objects.all()
        self.assertEqual(qs.count(), 4)
        export_qs = admin_reports.export_results_queryset(
            tally_id=self.tally.id, qs=qs
        )
        self.assertEqual(export_qs.count(), 2)
        data = {
            "select_1_ids": [1, 2],
            "select_2_ids": [1, 2],
            "election_level_names": ["Local", "National"],
            "sub_race_type_names": ["Presidential", "Parliamentary"],
            "ballot_status": ["available_for_release"],
            "station_status": ["active"],
            "candidate_status": ["active"],
            "percentage_processed": 75,
            "sub_con_codes": [self.sc.code],
        }
        export_qs = admin_reports.export_results_queryset(
            tally_id=self.tally.id, qs=qs, data=data
        )
        self.assertEqual(export_qs.count(), 0)

    def test_duplicate_results_queryset(self):
        qs = ResultForm.objects.all()
        self.assertEqual(qs.count(), 1)
        data = {"select_1_ids": [1, 2], "select_2_ids": [1, 2]}
        duplicate_qs = admin_reports.duplicate_results_queryset(
            tally_id=self.tally.id, qs=qs
        )
        self.assertEqual(duplicate_qs.count(), 1)
        duplicate_qs = admin_reports.duplicate_results_queryset(
            tally_id=self.tally.id, qs=qs, data=data
        )
        self.assertEqual(duplicate_qs.count(), 1)

    def test_generate_progressive_report_queryset(self):
        qs = Result.objects.all()
        self.assertEqual(qs.count(), 4)
        progres_qs = admin_reports.generate_progressive_report_queryset(
            tally_id=self.tally.id, qs=qs
        )
        self.assertEqual(progres_qs.count(), 1)
        data = [
            {
                "select_1_ids": [1, 2],
                "select_2_ids": [1, 2],
                "region_id": self.region.id,
            }
        ]
        progres_qs = admin_reports.generate_progressive_report_queryset(
            tally_id=self.tally.id, qs=qs, data=data
        )
        self.assertEqual(progres_qs.count(), 1)

    def test_custom_queryset_filter(self):
        data = [
            {
                "select_1_ids": [1, 2],
                "select_2_ids": [1, 2],
                "region_id": self.region.id,
            }
        ]
        kwargs1 = {
            "region_id": self.region.id,
            "constituency_id": self.constituency.id,
            "report_type": "turnout",
        }
        kwargs2 = {
            "region_id": self.region.id,
            "constituency_id": self.constituency.id,
            "report_type": "summary",
        }
        qs = ReconciliationForm.objects.all()
        self.assertEqual(qs.count(), 1)
        custom_qs = admin_reports.custom_queryset_filter(
            self.tally.id, qs, data, **kwargs1
        )
        self.assertEqual(custom_qs.count(), 1)
        cus_qs = admin_reports.custom_queryset_filter(
            self.tally.id, qs, data, **kwargs2
        )
        self.assertEqual(cus_qs.count(), 1)

    def test_stations_and_centers_queryset(self):
        rf_qs = ResultForm.objects.all()
        s_qs = Station.objects.all()
        data = [
            {
                "select_1_ids": [1, 2],
                "select_2_ids": [1, 2],
                "region_id": self.region.id,
            }
        ]
        kwargs = []

        discrepancy_reports = [
            "stations-and-centers-under-process-audit-list",
            "stations-and-centers-under-investigation-list",
            "stations-and-centers-excluded-after-investigation-list",
        ]
        for report in discrepancy_reports:
            kwarg = {
                "region_id": self.region.id,
                "constituency_id": self.constituency.id,
                "report_type": report,
            }
            kwargs.append(kwarg)

        for kwarg in kwargs:
            if (
                kwarg["report_type"]
                == "stations-and-centers-under-process-audit-list"
            ):
                qs = rf_qs
                qs = admin_reports.stations_and_centers_queryset(
                    self.tally.id, qs, data, **kwarg
                )
                self.assertEqual(qs.count(), 1)
            else:
                qs = s_qs
                qs = admin_reports.stations_and_centers_queryset(
                    self.tally.id, qs, data, **kwarg
                )
                self.assertEqual(qs.count(), 0)

    def test_get_centers_stations(self):
        center_ids = [center.id for center in Center.objects.all()]
        data = {"tally_id": self.tally.id, "center_ids": center_ids}
        request = self.factory.get("/")
        request.user = self.user
        request.GET = {"data": json.dumps(data)}
        response = admin_reports.get_centers_stations(request)
        self.assertEqual(response.status_code, 200)
        station_ids = [station.id for station in Station.objects.all()]
        self.assertEqual(
            json.loads(response.content.decode())["station_ids"], station_ids
        )

    def test_get_export(self):
        center_ids = [center.id for center in Center.objects.all()]
        station_ids = [station.id for station in Station.objects.all()]
        data = {
            "tally_id": self.tally.id,
            "export_number": 1,
            "exportType": "PPT",
            "select_1_ids": center_ids,
            "select_2_ids": station_ids,
            "sub_con_codes": [self.sc.code],
        }
        request = self.factory.get("/")
        request.user = self.user
        request.GET = {"data": json.dumps(data)}
        response = admin_reports.get_export(request)
        self.assertEqual(response.status_code, 200)


class TestClearanceAuditSummaryReportViews(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally,
            election_level="Municipal",
            ballot_name="Individual",
        )
        ballot = create_ballot(
            self.tally,
            electrol_race=self.electrol_race,
        )
        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc = create_sub_constituency(
            code=1,
            field_office="1",
            ballots=[ballot],
            tally=self.tally,
        )
        center, _ = Center.objects.get_or_create(
            code=1,
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
        self.station = create_station(
            center=center,
            registrants=50,
            tally=self.tally,
            station_number=1,
            gender=Gender.MALE,
        )
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.CLEARANCE,
            office=office,
            center=center,
            station_number=self.station.station_number,
            ballot=ballot,
        )
        create_clearance(self.result_form, user=self.user)
        self.result_form.save()

    def test_clearance_audit_summary_report_view_renders(self):
        """
        Test that the clearance audit summary report view renders correctly
        """
        from bs4 import BeautifulSoup

        from tally_ho.apps.tally.views.reports import \
            administrative_areas_reports as aar

        request = self.factory.get(
            reverse(
                "clearance-audit-summary", kwargs={"tally_id": self.tally.pk}
            )
        )
        request.user = self.user
        request.session = {}
        response = aar.ClearanceAuditSummaryReportView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = (
            response.rendered_content
            if hasattr(response, "rendered_content")
            else response.content.decode()
        )
        doc = BeautifulSoup(content, "html.parser")
        table_headers = [th.text.strip() for th in doc.find_all("th")]
        expected_headers = [
            "Barcode",
            "Center Code",
            "Station Number",
            "Race",
            "Sub Race",
            "Municipality Name",
            "Action Prior",
            "Recommendation",
            "Decision",
            "Issue Reason",
            "Supervisor",
            "Last Modified",
        ]
        self.assertTrue(
            any(header in table_headers for header in expected_headers)
        )
        remote_url = reverse(
            "clearance-audit-summary-data", kwargs={"tally_id": self.tally.pk}
        )
        self.assertIn(str(self.tally.pk), content)
        self.assertIn(remote_url, content)
        self.assertIn("deployedSiteUrl", content)

    def test_clearance_audit_summary_report_data_view_returns_data(self):
        """
        Test that the clearance audit summary report data view returns data
        """
        from tally_ho.apps.tally.views.reports import \
            administrative_areas_reports as aar

        url = reverse(
            "clearance-audit-summary-data", kwargs={"tally_id": self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = self.user
        request.session = {}
        response = aar.ClearanceAuditSummaryReportDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertIn("data", content)
        self.assertGreaterEqual(len(content["data"]), 1)
        row = content["data"][0]
        expected_keys = [
            "barcode",
            "center_code",
            "station_number",
            "race",
            "sub_race",
            "municipality_name",
            "municipality_code",
            "action_prior",
            "recommendation",
            "decision",
            "issue_reason",
            "supervisor",
            "last_modified",
        ]
        for key in expected_keys:
            self.assertIn(key, row)
        self.assertEqual(row["barcode"], self.result_form.barcode)
        self.assertEqual(row["center_code"], self.result_form.center.code)

    def test_clearance_audit_summary_report_data_view_filtering(self):
        """
        Test that the clearance audit summary report data view filters data
        """
        from tally_ho.apps.tally.views.reports import \
            administrative_areas_reports as aar

        url = reverse(
            "clearance-audit-summary-data", kwargs={"tally_id": self.tally.pk}
        )
        # Filter by race
        data = {"election_level_names": ["Municipal"]}
        request = self.factory.get(url, {"data": str(data)})
        request.user = self.user
        request.session = {}
        response = aar.ClearanceAuditSummaryReportDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        for row in content["data"]:
            self.assertEqual(row["race"], "Municipal")

    def test_clearance_audit_summary_report_data_view_pagination(self):
        """
        Test that the clearance audit summary report data view paginates data
        """
        from tally_ho.apps.tally.views.reports import \
            administrative_areas_reports as aar

        url = reverse(
            "clearance-audit-summary-data", kwargs={"tally_id": self.tally.pk}
        )
        request = self.factory.get(url, {"start": 0, "length": 1})
        request.user = self.user
        request.session = {}
        response = aar.ClearanceAuditSummaryReportDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content["data"]), 1)
        row = content["data"][0]
        self.assertEqual(row["barcode"], self.result_form.barcode)

    def test_clearance_audit_summary_report_view_requires_login(self):
        """
        Test that the clearance audit summary report view requires login
        """
        from tally_ho.apps.tally.views.reports import \
            administrative_areas_reports as aar

        url = reverse(
            "clearance-audit-summary", kwargs={"tally_id": self.tally.pk}
        )
        request = self.factory.get(url)
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        request.session = {}
        response = aar.ClearanceAuditSummaryReportView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertIn(response.status_code, [302, 403])

    def test_clearance_audit_summary_report_data_view_empty(self):
        """
        Test that the clearance audit summary report data view returns empty
        data
        """
        from tally_ho.apps.tally.views.reports import \
            administrative_areas_reports as aar

        # Remove clearance from the form
        self.result_form.clearances.all().delete()
        self.result_form.form_state = FormState.ARCHIVED
        self.result_form.save()
        url = reverse(
            "clearance-audit-summary-data", kwargs={"tally_id": self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = self.user
        request.session = {}
        response = aar.ClearanceAuditSummaryReportDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertEqual(len(content["data"]), 0)
