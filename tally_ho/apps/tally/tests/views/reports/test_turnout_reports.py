from django.test import RequestFactory

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.views.reports import turnout_reports
from tally_ho.libs.tests.test_base import create_result_form,\
    create_station, create_reconciliation_form, create_tally,\
    create_center, create_region, create_constituency, create_office, TestBase


class TestTurnoutReports(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

    def test_regions_turnout_report(self):
        """
        Test that the region turnout report is rendered as expected.
        """
        tally = create_tally()
        tally.users.add(self.user)

        region = create_region(tally=tally)
        office = create_office(tally=tally, region=region)
        center = create_center()
        station = create_station(center=center, registrants=20)
        result_form = create_result_form(
            tally=tally,
            office=office,
            center=center,
            station_number=station.station_number)
        create_reconciliation_form(
            result_form=result_form,
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

        request = self._get_request()
        view = turnout_reports.RegionsTurnoutReportView.as_view()
        request = self.factory.get('/reports-regions')
        request.user = self.user
        response = view(
            request,
            tally_id=tally.pk,
            group_name=groups.TALLY_MANAGER)

        regions_turnout_report =\
            turnout_reports.generate_voters_turnout_report(
                tally.id, 'result_form__office__region__name')[0]

        self.assertContains(response, "<h1>Region Reports</h1>")
        self.assertContains(response, "<h3>Turn Report per Region</h3>")
        self.assertContains(response, "<th>Region Name</th>")
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
            str('<td>'
                f'{regions_turnout_report["total_number_of_ballots_used"]}'
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

    def test_constituency_turnout_report(self):
        """
        Test that the constituency turnout report is rendered as expected.
        """
        tally = create_tally()
        tally.users.add(self.user)

        constituency = create_constituency(tally=tally)
        center = create_center(tally=tally, constituency=constituency)
        station = create_station(center=center, registrants=20)
        result_form = create_result_form(
            tally=tally,
            center=center,
            station_number=station.station_number)
        create_reconciliation_form(
            result_form=result_form,
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

        request = self._get_request()
        view = turnout_reports.ConstituencyTurnoutReportView.as_view()
        request = self.factory.get('/reports-constituencies')
        request.user = self.user
        response = view(
            request,
            tally_id=tally.pk,
            group_name=groups.TALLY_MANAGER)

        turnout_report =\
            turnout_reports.generate_voters_turnout_report(
                tally.id, 'result_form__center__constituency__name')[0]

        self.assertContains(response, "<h1>Constituency Reports</h1>")
        self.assertContains(response, "<h3>Turn Report per Constituency</h3>")
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
