from django.test import RequestFactory

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.views.reports import administrative_areas_reports
from tally_ho.libs.tests.test_base import create_result_form,\
    create_station, create_reconciliation_form, create_tally,\
    create_center, create_region, create_constituency, create_office, TestBase


class TestReports(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)

        region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=region)
        constituency = create_constituency(tally=self.tally)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office='1')
        center = create_center(tally=self.tally,
                               sub_constituency=sc,
                               constituency=constituency)
        station = create_station(center=center, registrants=20)
        result_form = create_result_form(
            tally=self.tally,
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

    def test_regions_reports(self):
        """
        Test that the region reports are rendered as expected.
        """
        request = self._get_request()
        view = administrative_areas_reports.RegionsReportsView.as_view()
        request = self.factory.get('/reports-regions')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        regions_turnout_report =\
            administrative_areas_reports.generate_voters_turnout_report(
                self.tally.id, 'result_form__office__region__name')[0]

        self.assertContains(response, "<h1>Region Reports</h1>")

        # Region turnout report tests
        self.assertContains(response, "<h3>Turn Out Report</h3>")
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

        votes_summary_report =\
            administrative_areas_reports.generate_votes_summary_report(
                self.tally.id, 'result_form__office__region__name')[0]

        # Region votes summary report tests
        self.assertContains(response, "<h3>Votes Summary Report</h3>")
        self.assertContains(response, "<th>Region Name</th>")
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

    def test_constituency_reports(self):
        """
        Test that the constituency reports are rendered as expected.
        """
        request = self._get_request()
        view = administrative_areas_reports.ConstituencyReportsView.as_view()
        request = self.factory.get('/reports-constituencies')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        turnout_report =\
            administrative_areas_reports.generate_voters_turnout_report(
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
            administrative_areas_reports.generate_votes_summary_report(
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
            administrative_areas_reports.SubConstituencyReportsView.as_view()
        request = self.factory.get('/reports-sub-constituencies')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.TALLY_MANAGER)

        turnout_report =\
            administrative_areas_reports.generate_voters_turnout_report(
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
            administrative_areas_reports.generate_votes_summary_report(
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
