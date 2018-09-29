from django.test import RequestFactory

from tally_ho.apps.tally.views.reports import offices
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    create_center,
    create_ballot,
    create_result_form,
    create_tally,
    TestBase,
)


class TestOffices(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_overview_report_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        for i in range(1, 11):
            center = create_center(tally=tally)
            ballot = create_ballot(tally=tally)
            create_result_form(
                center=center, ballot=ballot,
                station_number=i,
                tally=tally,
                barcode=i,
                serial_number=i,
                form_state=i - 1)

        request = self._get_request()
        view = offices.OfficesReportView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertContains(response, 'Per Office')
        self.assertContains(response, 'Tally Center Progress Report')
        self.assertContains(response, "<td>Not Received</td>")
