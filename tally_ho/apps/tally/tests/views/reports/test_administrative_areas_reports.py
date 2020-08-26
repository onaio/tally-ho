import json
from django.test import RequestFactory

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.center import Center
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.apps.tally.views.reports import (
    administrative_areas_reports as admin_reports,
)
from tally_ho.apps.tally.views.data import center_list_view
from tally_ho.libs.tests.test_base import create_result_form,\
    create_station, create_reconciliation_form, create_tally,\
    create_region, create_constituency, create_office, create_result,\
    create_candidates, TestBase


class TestAdministrativeAreasReports(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)

        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        constituency = create_constituency(tally=self.tally)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office='1')
        center, _ = Center.objects.get_or_create(
            code='1',
            mahalla='1',
            name='1',
            office=office,
            region='1',
            village='1',
            active=True,
            tally=self.tally,
            sub_constituency=sc,
            center_type=CenterType.GENERAL,
            constituency=constituency)
        self.station = create_station(
            center=center, registrants=20, tally=self.tally)
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station.station_number)
        create_reconciliation_form(
            result_form=self.result_form,
            user=self.user,
            number_ballots_inside_box=20,
            number_cancelled_ballots=0,
            number_spoiled_ballots=0,
            number_unstamped_ballots=0,
            number_unused_ballots=0,
            number_valid_votes=20,
            number_invalid_votes=0,
            number_ballots_received=20,
        )
        votes = 20
        create_candidates(self.result_form, votes=votes, user=self.user,
                          num_results=1)
        for result in self.result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(self.result_form, result.candidate, self.user, votes)

    def test_regions_reports(self):
        """
        Test that the region reports are rendered as expected.
        """
        request = self._get_request()
        view = admin_reports.RegionsReportsView.as_view()
        request = self.factory.get('/reports-regions')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        regions_turnout_report =\
            admin_reports.generate_report(
                tally_id=self.tally.id,
                report_column_name='result_form__office__region__name',
                report_type_name=admin_reports.report_types[1],)[0]

        self.assertContains(response, "<h1>Region Reports</h1>")

        # Region turnout report tests
        self.assertContains(response, "<h3>Turn Out Report</h3>")
        self.assertContains(response, "<th>Name</th>")
        self.assertContains(response, "<th>Total number of voters</th>")
        self.assertContains(response, "<th>Number of voters voted</th>")
        self.assertContains(response, "<th>Male voters</th>")
        self.assertContains(response, "<th>Female voters</th>")
        self.assertContains(response, "<th>Turnout percentage</th>")
        self.assertContains(
            response,
            f'<td>{regions_turnout_report["name"]}</td>')
        self.assertContains(
            response,
            f'<td>{regions_turnout_report["number_of_voters_voted"]}</td>')
        self.assertContains(
            response,
            str('<td>'
                f'{regions_turnout_report["total_number_of_registrants"]}'
                '</td>'))
        self.assertContains(
            response,
            f'<td>{regions_turnout_report["male_voters"]}</td>')
        self.assertContains(
            response,
            f'<td>{regions_turnout_report["female_voters"]}</td>')
        self.assertContains(
            response,
            f'<td>{regions_turnout_report["turnout_percentage"]} %</td>')

        votes_summary_report =\
            admin_reports.generate_report(
                tally_id=self.tally.id,
                report_column_name='result_form__office__region__name',
                report_type_name=admin_reports.report_types[2],)[0]

        # Region votes summary report tests
        self.assertContains(response, "<h3>Votes Summary Report</h3>")
        self.assertContains(response, "<th>Name</th>")
        self.assertContains(response, "<th>Total number of valid votes</th>")
        self.assertContains(response, "<th>Total number of invalid votes</th>")
        self.assertContains(
            response, "<th>Total number of cancelled votes</th>")
        self.assertContains(
            response,
            f'<td>{votes_summary_report["name"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_valid_votes"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_invalid_votes"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_cancelled_ballots"]}</td>')

        progressive_report =\
            admin_reports.generate_progressive_report(
                tally_id=self.tally.id,
                report_column_name='result_form__office__region__name',)[0]

        # Region progressive report tests
        self.assertContains(response, "<h2>Progressive Report</h2>")
        self.assertContains(response, "<th>Name</th>")
        self.assertContains(response, "<th>Number of Candidates</th>")
        self.assertContains(response, "<th>Number of Votes</th>")
        self.assertContains(
            response,
            f'<td>{progressive_report["name"]}</td>')
        self.assertContains(
            response,
            f'<td>{progressive_report["total_candidates"]}</td>')
        self.assertContains(
            response,
            f'<td>{progressive_report["total_votes"]}</td>')
        self.assertContains(
            response,
            'Region Constituencies Progressive Report')
        self.assertContains(
            response,
            'Region votes per candidate')

    def test_regions_centers_and_stations_in_audit_report(self):
        """
        Test that regions centers and stations in audit report is rendered as
        expected.
        """
        self.result_form.form_state = FormState.AUDIT
        self.result_form.save()

        request = self._get_request()
        view = admin_reports.RegionsReportsView.as_view()
        request = self.factory.get('/reports-regions')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        region_forms_in_audit =\
            admin_reports.get_admin_areas_with_forms_in_audit(
                tally_id=self.tally.id,
                report_column_name='office__region__name',)[0]
        total_num_of_centers_and_stations_in_audit =\
            region_forms_in_audit["total_num_of_centers_and_stations_in_audit"]

        # Region centers and stations in audit report tests
        self.assertContains(response, "<h2>Process Discrepancy Reports</h2>")
        self.assertContains(
            response, "<h4>Stations and Centers under process audit</h4>")
        self.assertContains(response, "<th>Name</th>")
        self.assertContains(response, "<th>Centers in Audit</th>")
        self.assertContains(response, "<th>Stations in Audit</th>")
        self.assertContains(response, "<th>Total</th>")
        self.assertContains(
            response,
            f'<td>{region_forms_in_audit["admin_area_name"]}</td>')
        self.assertContains(
            response,
            str('<td>'
                f'{region_forms_in_audit["number_of_centers_in_audit_state"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{region_forms_in_audit["number_of_stations_in_audit_state"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{total_num_of_centers_and_stations_in_audit}'
                '</td>'))
        self.assertContains(
            response,
            'Region Constituencies under process Audit')
        self.assertContains(
            response,
            'Region Centers and Stations under process Audit')

    def test_regions_centers_and_stations_in_audit_list_report(self):
        """
        Test that regions centers and stations in audit list report is
        rendered as expected.
        """
        tally_id = self.tally.pk
        region_id = self.region.pk
        self.result_form.form_state = FormState.AUDIT
        self.result_form.save()

        request = self._get_request()
        view = admin_reports.RegionsReportsView.as_view()
        request = self.factory.get('/reports-regions')
        request.user = self.user
        request.session = {}
        response = view(
            request,
            tally_id=tally_id,
            report_type='centers-and-stations-in-audit-report',
            region_id=region_id,
            group_name=groups.TALLY_MANAGER)

        self.assertEquals(response.status_code, 302)
        self.assertIn(f'/data/center-list/{tally_id}/{region_id}/',
                      response['location'])

        session = request.session
        request = self.factory.get(
            f'center-list-data/{tally_id}/{region_id}/')
        request.user = self.user
        request.session = session
        view = center_list_view.CenterListDataView.as_view()
        response = view(
            request,
            tally_id=tally_id,
            region_id=region_id)

        office, voting_district, center_name, center_code, station_number,\
            gender, registrants, received, archived, center_enabled,\
            station_enabled, edit_link = json.loads(
                response.content.decode())['data'][0]
        center_edit_link =\
            f"/super-administrator/edit-center/{tally_id}/{center_code}"
        station_edit_link =\
            f"/super-administrator/edit-station/{tally_id}/{self.station.pk}"

        self.assertEquals(office, self.station.center.office.name)
        self.assertEquals(voting_district, str(
            self.station.sub_constituency.code))
        self.assertEquals(center_name, self.station.center.name)
        self.assertEquals(center_code, str(self.station.center.code))
        self.assertEquals(station_number, str(self.station.station_number))
        self.assertEquals(gender, self.station.gender.label)
        self.assertEquals(registrants, str(self.station.registrants))
        self.assertEquals(
            received,
            str(("%.2f" % round(self.station.percent_received, 2))))
        self.assertEquals(
            archived,
            str(("%.2f" % round(self.station.percent_archived, 2))))
        self.assertEquals(center_enabled, str(self.station.center.active))
        self.assertEquals(station_enabled, str(self.station.active))
        self.assertEquals(
            edit_link,
            str(f'<a href="{center_edit_link}"'
                ' class="btn btn-default btn-small vertical-margin">Center</a>'
                f'<a href="{station_edit_link}"'
                ' class="btn btn-default btn-small vertical-margin">Station'
                '</a>'))

    def test_regions_centers_and_stations_under_investigation_report(self):
        """
        Test that regions centers and stations under investigation report is
        rendered as expected.
        """
        self.station.active = False
        self.station.disable_reason = DisableReason.NOT_OPENED
        self.station.save()

        request = self._get_request()
        view = admin_reports.RegionsReportsView.as_view()
        request = self.factory.get('/reports-regions')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        centers_stations_under_invg =\
            admin_reports.get_stations_and_centers_by_admin_area(
                tally_id=self.tally.id,
                report_column_name='center__office__region__name',
                report_type_name=admin_reports.report_types[3],)[0]
        total_number_of_centers_and_stations =\
            centers_stations_under_invg["total_number_of_centers_and_stations"]

        # Region centers and stations under investigation report tests
        self.assertContains(
            response, "<h4>Stations and Centers under Investigation</h4>")
        self.assertContains(response, "<th>Name</th>")
        self.assertContains(response, "<th>Centers</th>")
        self.assertContains(response, "<th>Stations</th>")
        self.assertContains(response, "<th>Total</th>")
        self.assertContains(
            response,
            f'<td>{centers_stations_under_invg["admin_area_name"]}</td>')
        self.assertContains(
            response,
            str('<td>'
                f'{centers_stations_under_invg["number_of_centers"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{centers_stations_under_invg["number_of_stations"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{total_number_of_centers_and_stations}'
                '</td>'))
        self.assertContains(
            response,
            'Region Constituencies under Investigation')
        self.assertContains(
            response,
            'Region Centers and Stations under Investigation')

    def test_regions_centers_and_stations_excluded_after_investigation(self):
        """
        Test that regions centers and stations excluded after investigation
        report is rendered as expected.
        """
        # Disable station
        self.station.active = False
        self.station.disable_reason = DisableReason.NOT_OPENED
        self.station.save()

        # Enable station
        self.station.active = True
        self.station.save()

        request = self._get_request()
        view = admin_reports.RegionsReportsView.as_view()
        request = self.factory.get('/reports-regions')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        centers_stations_ex_after_invg =\
            admin_reports.get_stations_and_centers_by_admin_area(
                tally_id=self.tally.id,
                report_column_name='center__office__region__name',
                report_type_name=admin_reports.report_types[4],)[0]
        total_number_of_centers_and_stations =\
            centers_stations_ex_after_invg[str(
                "total_number_of_centers_and_stations"
            )]

        # Region centers and stations excluded after investigation tests
        self.assertContains(
            response, "<h4>Stations and Centers under Investigation</h4>")
        self.assertContains(response, "<th>Name</th>")
        self.assertContains(response, "<th>Centers</th>")
        self.assertContains(response, "<th>Stations</th>")
        self.assertContains(response, "<th>Total</th>")
        self.assertContains(
            response,
            f'<td>{centers_stations_ex_after_invg["admin_area_name"]}</td>')
        self.assertContains(
            response,
            str('<td>'
                f'{centers_stations_ex_after_invg["number_of_centers"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{centers_stations_ex_after_invg["number_of_stations"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{total_number_of_centers_and_stations}'
                '</td>'))
        self.assertContains(
            response,
            'Region Constituencies excluded after investigation')
        self.assertContains(
            response,
            'Region Centers and Stations excluded after investigation')

    def test_constituency_reports(self):
        """
        Test that the constituency reports are rendered as expected.
        """
        request = self._get_request()
        view = admin_reports.ConstituencyReportsView.as_view()
        request = self.factory.get('/reports-constituencies')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        turnout_report =\
            admin_reports.generate_voters_turnout_report(
                self.tally.id, 'result_form__center__constituency__name')[0]

        self.assertContains(response, "<h1>Constituency Reports</h1>")

        # Constituency turnout report tests
        self.assertContains(response, "<h3>Turn Out Report</h3>")
        self.assertContains(response, "<th>Constituency Name</th>")
        self.assertContains(response, "<th>Total number of voters</th>")
        self.assertContains(response, "<th>Number of voters voted</th>")
        self.assertContains(response, "<th>Male voters</th>")
        self.assertContains(response, "<th>Female voters</th>")
        self.assertContains(response, "<th>Turnout percentage</th>")
        self.assertContains(
            response,
            f'<td>{turnout_report["name"]}</td>')
        self.assertContains(
            response,
            f'<td>{turnout_report["number_of_voters_voted"]}</td>')
        self.assertContains(
            response,
            str('<td>'
                f'{turnout_report["total_number_of_registrants"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{turnout_report["total_number_of_ballots_used"]}'
                '</td>'))
        self.assertContains(
            response,
            f'<td>{turnout_report["male_voters"]}</td>')
        self.assertContains(
            response,
            f'<td>{turnout_report["female_voters"]}</td>')
        self.assertContains(
            response,
            f'<td>{turnout_report["turnout_percentage"]} %</td>')

        votes_summary_report =\
            admin_reports.generate_votes_summary_report(
                self.tally.id, 'result_form__center__constituency__name')[0]

        # Constituency votes summary report tests
        self.assertContains(response, "<h3>Votes Summary Report</h3>")
        self.assertContains(response, "<th>Constituency Name</th>")
        self.assertContains(response, "<th>Total number of valid votes</th>")
        self.assertContains(response, "<th>Total number of invalid votes</th>")
        self.assertContains(
            response, "<th>Total number of cancelled votes</th>")
        self.assertContains(
            response,
            f'<td>{votes_summary_report["name"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_valid_votes"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_invalid_votes"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_cancelled_ballots"]}</td>')

    def test_sub_constituency_reports(self):
        """
        Test that the sub constituency reports are rendered as expected.
        """
        request = self._get_request()
        view =\
            admin_reports.SubConstituencyReportsView.as_view()
        request = self.factory.get('/reports-sub-constituencies')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        turnout_report =\
            admin_reports.generate_voters_turnout_report(
                self.tally.id,
                'result_form__center__sub_constituency__code')[0]

        self.assertContains(response, "<h1>Sub Constituency Reports</h1>")

        # Sub Constituency turnout report tests
        self.assertContains(response, "<h3>Turn Out Report</h3>")
        self.assertContains(response, "<th>Sub Constituency Name</th>")
        self.assertContains(response, "<th>Total number of voters</th>")
        self.assertContains(response, "<th>Number of voters voted</th>")
        self.assertContains(response, "<th>Male voters</th>")
        self.assertContains(response, "<th>Female voters</th>")
        self.assertContains(response, "<th>Turnout percentage</th>")
        self.assertContains(
            response,
            f'<td>{turnout_report["name"]}</td>')
        self.assertContains(
            response,
            f'<td>{turnout_report["number_of_voters_voted"]}</td>')
        self.assertContains(
            response,
            str('<td>'
                f'{turnout_report["total_number_of_registrants"]}'
                '</td>'))
        self.assertContains(
            response,
            str('<td>'
                f'{turnout_report["total_number_of_ballots_used"]}'
                '</td>'))
        self.assertContains(
            response,
            f'<td>{turnout_report["male_voters"]}</td>')
        self.assertContains(
            response,
            f'<td>{turnout_report["female_voters"]}</td>')
        self.assertContains(
            response,
            f'<td>{turnout_report["turnout_percentage"]} %</td>')

        votes_summary_report =\
            admin_reports.generate_votes_summary_report(
                self.tally.id,
                'result_form__center__sub_constituency__code')[0]

        # Sub Constituency votes summary report tests
        self.assertContains(response, "<h3>Votes Summary Report</h3>")
        self.assertContains(response, "<th>Sub Constituency Name</th>")
        self.assertContains(response, "<th>Total number of valid votes</th>")
        self.assertContains(response, "<th>Total number of invalid votes</th>")
        self.assertContains(
            response, "<th>Total number of cancelled votes</th>")
        self.assertContains(
            response,
            f'<td>{votes_summary_report["name"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_valid_votes"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_invalid_votes"]}</td>')
        self.assertContains(
            response,
            f'<td>{votes_summary_report["number_cancelled_ballots"]}</td>')
