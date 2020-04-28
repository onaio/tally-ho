from django.test import RequestFactory

from tally_ho.apps.tally.views.data import candidate_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import\
    create_tally, create_office, TestBase


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
        request = self.factory.get('/candidate-list')
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Candidate List")

    def test_candidate_list_per_office_view_get(self):
        """
        Test that candidate list per office view renders correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        office = create_office(tally=tally)
        view = views.CandidateListView.as_view()
        request = self.factory.get('/candidate-list-per-office')
        request.user = self.user
        response = view(request, tally_id=tally.pk, office_id=office.id)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Candidate List Per Office")
