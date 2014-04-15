from django.test import RequestFactory

from tally_ho.apps.tally.views.data import form_list_view as views
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_ballot, TestBase


class TestFormListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_form_not_received_list_view(self):
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Forms Not Received")

    def test_form_not_received_list_csv_view(self):
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, format='csv')
        self.assertContains(response, "barcode")

    def test_forms_for_race(self):
        ballot = create_ballot()
        view = views.FormsForRaceView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, ballot=ballot.number)
        self.assertContains(response, "Forms for Race %s" % ballot.number)
