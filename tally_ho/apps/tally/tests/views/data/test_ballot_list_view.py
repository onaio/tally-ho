from django.test import RequestFactory

from tally_ho.apps.tally.views.data import ballot_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally, TestBase


class TestBallotListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_ballot_list_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.BallotListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Ballot List")
        self.assertContains(response, "New Ballot")
