from django.test import RequestFactory

from tally_ho.apps.tally.views.data import candidate_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import\
    create_tally, TestBase


class TestCandidateListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_candidate_list_view_get(self):
        """
        Test that candidate list view renders correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CandidateListView.as_view()
        request = self.factory.get('/candidate-list-data')
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Candidate List")
