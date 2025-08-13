import json

from django.test import RequestFactory

from tally_ho.apps.tally.views.reports import station_progress_report as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_center,
    create_result_form,
    create_station,
    create_tally,
)


class StationProgressListView(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_station_progress_list_view(self):
        """
        Test that station progress list view renders correctly
        """
        tally = create_tally()
        tally.users.add(self.user)
        view = views.StationProgressListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Station Progess Report")

    def test_station_progress_list_data_view(self):
        """
        Test that station progress list data view returns correct data
        """
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center=center, tally=tally)
        create_result_form(
            form_state=FormState.ARCHIVED,
            center=center,
            tally=tally,
            station_number=station.station_number)
        view = views.StationProgressListDataView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, tally_id=tally.pk)

        office_name, sub_constituency_name, sub_constituency_code,\
            center_name, center_code, station_number, gender, registrants,\
                active = json.loads(
                response.content.decode())['data'][0]

        self.assertEqual(office_name, str(station.center.office.name))
        self.assertEqual(sub_constituency_name, str(
            station.sub_constituency.name))
        self.assertEqual(sub_constituency_code, str(
            station.sub_constituency.code))
        self.assertEqual(office_name, str(station.center.office.name))
        self.assertEqual(center_name, str(station.center.name))
        self.assertEqual(center_code, str(station.center.code))
        self.assertEqual(station_number, str(station.station_number))
        self.assertEqual(gender, str(station.gender.name.capitalize()))
        self.assertEqual(registrants, str(station.registrants))
        self.assertEqual(active, str(station.active))
