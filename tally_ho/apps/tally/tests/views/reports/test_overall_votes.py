from django.test import RequestFactory

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.views.reports import overall_votes
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.tests.test_base import create_result_form, create_ballot,\
    create_candidates, create_result, create_tally, create_center,\
    create_station, TestBase


class TestOverallVotes(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)

        ballot = create_ballot(tally=self.tally)
        center = create_center('12345', tally=self.tally)
        station = create_station(center)
        result_form = create_result_form(
            tally=self.tally,
            ballot=ballot,
            center=center,
            station_number=station.station_number)
        votes = 12
        create_candidates(result_form, votes=votes, user=self.user,
                          num_results=1)
        for result in result_form.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form, result.candidate, self.user, votes)

    def test_station_overall_votes_get(self):
        """Test that Station overall votes page is rendered"""
        request = self._get_request()
        view = overall_votes.OverallVotes.as_view()
        request = self.factory.get(
            f'/reports/internal/station-overall-votes/{self.tally.pk}')
        request.user = self.user
        request.session = {}
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.SUPER_ADMINISTRATOR)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Station Overall Progress")

    def test_center_overall_votes_get(self):
        """Test that Center overall votes page is rendered"""
        request = self._get_request()
        view = overall_votes.OverallVotes.as_view()
        request = self.factory.get(
            f'/reports/internal/center-overall-votes/{self.tally.pk}')
        request.user = self.user
        request.session = {}
        response = view(
            request,
            tally_id=self.tally.pk,
            group_name=groups.SUPER_ADMINISTRATOR)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Center Overall Progress")
