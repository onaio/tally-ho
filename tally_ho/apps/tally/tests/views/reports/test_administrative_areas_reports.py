import json
from django.test import RequestFactory

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.apps.tally.views.reports import (
    administrative_areas_reports as admin_reports,
)
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
        self.constituency = create_constituency(tally=self.tally)
        self.sc, _ =\
            SubConstituency.objects.get_or_create(code=1, field_office='1')
        center, _ = Center.objects.get_or_create(
            code='1',
            mahalla='1',
            name='1',
            office=office,
            region='1',
            village='1',
            active=True,
            tally=self.tally,
            sub_constituency=self.sc,
            center_type=CenterType.GENERAL,
            constituency=self.constituency)
        self.station = create_station(
            center=center, registrants=20, tally=self.tally)
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station.station_number)
        self.recon_form = create_reconciliation_form(
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
                          num_results=1, tally=self.tally)
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
        request = self._get_request()
        view = admin_reports.TurnoutReportDataView.as_view()
        request = self.factory.get('/sub-constituency-turnout-report')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk)

        # Sub Constituency turnout report tests
        code, number_of_voters_voted, total_number_of_registrants,\
            male_voters, female_voters, turnout_percentage, _, _, _ =\
            json.loads(
                response.content.decode())['data'][0]

        self.assertEquals(
            code, '<td class="center">{}</td>'.format(self.sc.code))
        self.assertEquals(
            number_of_voters_voted,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_ballots_received))
        self.assertEquals(total_number_of_registrants,
                          '<td class="center">{}</td>'.format(
                              self.station.registrants))
        self.assertEquals(male_voters, '<td class="center">20</td>')
        self.assertEquals(female_voters, '<td class="center">0</td>')
        self.assertEquals(turnout_percentage, '<td class="center">100%</td>')

        view = admin_reports.SummaryReportDataView.as_view()
        request = self.factory.get('/sub-constituency-summary-report')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk)

        # Sub Constituency votes summary report tests
        code, valid_votes, invalid_votes, cancelled_votes, _, _, _ =\
            json.loads(
                response.content.decode())['data'][0]

        self.assertEquals(
            code, '<td class="center">{}</td>'.format(self.sc.code))
        self.assertEquals(
            valid_votes,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_valid_votes))
        self.assertEquals(
            invalid_votes,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_invalid_votes))
        self.assertEquals(
            cancelled_votes,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_cancelled_ballots))

        view = admin_reports.ProgressiveReportDataView.as_view()
        request = self.factory.get('/sub-cons-progressive-report-list')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk)
        candidates_count = Candidate.objects.filter(
            tally__id=self.tally.pk).count()

        # Sub Constituency progressive report tests
        code, num_candidates, num_votes, _, _, _ =\
            json.loads(
                response.content.decode())['data'][0]

        self.assertEquals(
            code, '<td class="center">{}</td>'.format(self.sc.code))
        self.assertEquals(
            num_votes,
            '<td class="center">{}</td>'.format(
                self.result_form.num_votes))
        self.assertEquals(
            num_candidates,
            '<td class="center">{}</td>'.format(
                candidates_count))
