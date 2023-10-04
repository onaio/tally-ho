import json

from django.test import RequestFactory

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.apps.tally.views.reports import (
    administrative_areas_reports as admin_reports,
)
from tally_ho.libs.tests.test_base import (
    create_electrol_race, create_result_form, create_station,\
    create_reconciliation_form, create_sub_constituency, create_tally,\
    create_region, create_constituency, create_office, create_result,\
    create_candidates, TestBase, create_ballot
)
from tally_ho.libs.tests.fixtures.electrol_race_data import (
    electrol_races
)



class TestAdministrativeAreasReports(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally,
            **electrol_races[0]
        )
        ballot = create_ballot(self.tally, electrol_race=self.electrol_race)
        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc =\
            create_sub_constituency(code=1, field_office='1', ballots=[ballot])
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
            constituency=self.constituency
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
            ballot=ballot)
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
        create_candidates(
            self.result_form, votes=votes, user=self.user,
            num_results=1, tally=self.tally
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
        request = self.factory.post('/sub-constituency-summary-report')
        request.user = self.user
        response = view(
            request,
            tally_id=self.tally.pk,
            region_id=self.region.pk,
            constituency_id=self.constituency.pk
            )

        # Sub Constituency votes summary report tests
        code, valid_votes, invalid_votes, cancelled_votes, _, _, _ =\
            json.loads(
                response.content.decode())['data'][0]

        self.assertEqual(
            code, '<td class="center">{}</td>'.format(self.sc.code))
        self.assertEqual(
            valid_votes,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_valid_votes))
        self.assertEqual(
            invalid_votes,
            '<td class="center">{}</td>'.format(
                self.recon_form.number_invalid_votes))
        self.assertEqual(
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

        self.assertEqual(
            code, '<td class="center">{}</td>'.format(self.sc.code))
        self.assertEqual(
            num_votes,
            '<td class="center">{}</td>'.format(
                self.result_form.num_votes))
        self.assertEqual(
            num_candidates,
            '<td class="center">{}</td>'.format(
                candidates_count))

    def apply_filter(self, data):
        view = admin_reports.ResultFormResultsListDataView.as_view()
        request = self.factory.post('/form-results', data=data)
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
                        "election_level_names":
                        ["Presidential"],
                        "sub_race_type_names":
                        ["ballot_number_presidential_runoff"]
                    }
                )
            }
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 0)
        data = {
            "data": str(
                {
                        "election_level_names": ["Presidential"],
                        "sub_race_type_names": ["ballot_number_presidential"]
                    }
                )
            }
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 2)

        # test center filter
        data = {'data': '{"select_1_ids": ["-1"]}'}  # non existent id
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 0)
        center_id = self.station.center.id
        data = {'data': '{"select_1_ids": ' + f'["{center_id}"]' + '}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 2)

        # test stations filter
        data = {'data': '{"select_2_ids": ["-1"]}'}  # non existent id
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 0)
        station_id = self.station.id
        data = {'data': '{"select_2_ids": ' + f'["{station_id}"]' + '}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 2)

        # test ballot status filter
        data = {'data': '{"ballot_status": ["not_available_for_release"]}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 2)
        data = {'data': '{"ballot_status": ["available_for_release"]}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 0)

        # test station filter
        data = {'data': '{"station_status": ["active"]}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 2)
        data = {'data': '{"station_status": ["inactive"]}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 0)

        # test candidate status
        data = {'data': '{"candidate_status": ["active"]}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 2)
        data = {'data': '{"candidate_status": ["inactive"]}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 0)

        # test station percentage processed
        data = {'data': '{"percentage_processed": "10"}'}
        response = self.apply_filter(data)
        self.assertEqual(
            len(json.loads(response.content.decode())['data']), 2)
