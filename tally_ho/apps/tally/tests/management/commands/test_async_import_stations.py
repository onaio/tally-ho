from celery.contrib.testing.worker import start_worker
from django.test import TransactionTestCase

from tally_ho.apps.tally.management.commands.asign_ballots_to_sub_cons import (
    async_asign_ballots_to_sub_cons_from_ballots_file,
)
from tally_ho.apps.tally.management.commands.import_centers import (
    async_import_centers_from_centers_file,
)
from tally_ho.apps.tally.management.commands.import_electrol_races_and_ballots import (
    async_import_electrol_races_and_ballots_from_ballots_file as async_impt_electrol_races_ballots_tsk,
)
from tally_ho.apps.tally.management.commands.import_stations import (
    async_import_stations_from_stations_file,
)
from tally_ho.apps.tally.management.commands.import_sub_cons_and_cons import (
    async_import_sub_constituencies_and_constituencies_from_sub_cons_file as async_impt_sub_cons_and_cons_tsk,
)
from tally_ho.apps.tally.models.station import Station
from tally_ho.celeryapp import app
from tally_ho.libs.tests.test_base import create_tally


class AsyncImportStationsTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.celery_worker = start_worker(app,
                                         loglevel="info",
                                         perform_ping_check=False)
        cls.celery_worker.__enter__()
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.celery_worker.__exit__(None, None, None)

    def setUp(self):
        self.tally = create_tally()
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballots.csv'
        # Create electrol races and balllots
        async_impt_electrol_races_ballots_tsk(tally_id=self.tally.id,
                                              csv_file_path=csv_file_path,)
        # Create constituencies and sub constituencies
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/subcons.csv'
        async_impt_sub_cons_and_cons_tsk(tally_id=self.tally.id,
                                         csv_file_path=csv_file_path,)
        # Assign ballots to sub cons
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/subs_ballots.csv'
        async_asign_ballots_to_sub_cons_from_ballots_file(
            tally_id=self.tally.id,
            csv_file_path=csv_file_path,)
        # Create centers
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/centers.csv'
        async_import_centers_from_centers_file(tally_id=self.tally.id,
                                               csv_file_path=csv_file_path,)

    def test_async_import_stations(self):
        # Prepare test data
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/stations.csv'
        task = async_import_stations_from_stations_file.delay(
                        tally_id=self.tally.id,
                        csv_file_path=csv_file_path,)
        task.wait()

        # Assert that the Station objects are created
        stations = Station.objects.filter(tally=self.tally)
        self.assertGreater(stations.count(), 0)

    def test_async_import_stations_with_exception(self):
        # Prepare test data with faulty file
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballot_order.csv'

        # Call the task with faulty data that raises an exception
        with self.assertRaises(Exception):
            task = async_import_stations_from_stations_file.delay(
                        tally_id=self.tally.id,
                        csv_file_path=csv_file_path,)
            task.wait()
