import logging
from django.test import RequestFactory

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.management.commands.import_data import (
    process_results_form_row
)
from tally_ho.libs.tests.test_base import (
    create_ballot,
    create_center,
    create_station,
    create_tally,
    create_office,
    TestBase
)
from tally_ho.libs.permissions import groups


class TestImportData(TestBase):
    logger = logging.getLogger(__name__)
    gender = 'Male'
    name = 'Nairobi'
    office_name = 'office'
    barcode = '110010101'
    serial_number = '01000001'
    number = '12345'
    tally = None
    empty_string = ''

    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        create_office(name=self.office_name, tally=self.tally)

    def test_process_results_form_row_station_disabled_error(self):
        ballot = create_ballot(tally=self.tally)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office='1')
        center = create_center(self.number,
                               tally=self.tally,
                               sub_constituency=sc)
        station = create_station(center, active=False)
        row = [
            str(ballot.number),
            center.code,
            str(station.station_number),
            self.gender,
            self.name,
            self.office_name,
            self.empty_string,
            self.barcode,
            self.serial_number]

        with self.assertLogs(logger=self.logger, level='WARNING') as cm:
            process_results_form_row(tally=self.tally,
                                     row=row,
                                     logger=self.logger)
            self.assertIn(
                str('WARNING:%s:Selected station "%s" is disabled') %
                (self.logger.name, station.station_number), cm.output)

    def test_process_results_form_row_station_does_not_exist_error(self):
        ballot = create_ballot(tally=self.tally)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office='1')
        center = create_center(self.number,
                               tally=self.tally,
                               sub_constituency=sc)
        station_number = self.number
        row = [
            str(ballot.number),
            center.code,
            str(station_number),
            self.gender,
            self.name,
            self.office_name,
            self.empty_string,
            self.barcode,
            self.serial_number]

        with self.assertLogs(logger=self.logger, level='WARNING') as cm:
            process_results_form_row(tally=self.tally,
                                     row=row,
                                     logger=self.logger)
            self.assertIn(
                str('WARNING:%s:Station "%s" does not exist for center "%s"') %
                (self.logger.name, station_number, center.code), cm.output)

    def test_process_results_form_row_ballot_number_error(self):
        ballot = create_ballot(tally=self.tally)
        sc, _ = SubConstituency.objects.get_or_create(code=2, field_office='1')
        center = create_center(self.number,
                               tally=self.tally,
                               sub_constituency=sc)
        station = create_station(center)
        row = [
            str(ballot.number),
            center.code,
            str(station.station_number),
            self.gender,
            self.name,
            self.office_name,
            self.empty_string,
            self.barcode,
            self.serial_number]

        with self.assertLogs(logger=self.logger, level='WARNING') as cm:
            process_results_form_row(tally=self.tally,
                                     row=row,
                                     logger=self.logger)
            self.assertIn(
                str('WARNING:%s:Ballot number "%s" do not match for '
                    'center "%s" and station "%s"') %
                (self.logger.name,
                 ballot.number,
                 center.code,
                 station.station_number), cm.output)

    def test_process_results_form_row_office_name_error(self):
        ballot = create_ballot(tally=self.tally)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office='1')
        center = create_center(self.number,
                               tally=self.tally,
                               sub_constituency=sc)
        station = create_station(center)
        office_name = 'Mombasa'
        row = [
            str(ballot.number),
            center.code,
            str(station.station_number),
            self.gender,
            self.name,
            office_name,
            self.empty_string,
            self.barcode,
            self.serial_number]

        with self.assertLogs(logger=self.logger, level='WARNING') as cm:
            process_results_form_row(tally=self.tally,
                                     row=row,
                                     logger=self.logger)
            self.assertIn(str('WARNING:%s:Office "%s" does not exist') %
                          (self.logger.name, office_name), cm.output)

    def test_process_results_form_row_post(self):
        ballot = create_ballot(tally=self.tally)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office='1')
        center = create_center(self.number,
                               tally=self.tally,
                               sub_constituency=sc)
        station = create_station(center)
        row = [
            str(ballot.number),
            center.code,
            str(station.station_number),
            self.gender,
            self.name,
            self.office_name,
            self.empty_string,
            self.barcode,
            self.serial_number]
        process_results_form_row(tally=self.tally, row=row, logger=self.logger)
        form = ResultForm.objects.get(barcode=self.barcode, tally=self.tally)
        self.assertEqual(form.barcode, self.barcode)
