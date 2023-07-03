from django.test import TransactionTestCase
from celery.contrib.testing.worker import start_worker

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.management.commands.import_electrol_races_and_ballots\
    import (
        async_import_electrol_races_and_ballots_from_ballots_file as async_tsk
    )
from tally_ho.libs.tests.test_base import create_tally
from tally_ho.celeryapp import app

class ImportElectrolRacesAndBallotsTestCase(TransactionTestCase):
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

    def test_import_electrol_races_and_ballots(self):
        # Prepare test data
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballots.csv'
        task = async_tsk.delay(tally_id=self.tally.id,
                               csv_file_path=csv_file_path,)
        task.wait()

        # Assert that the ElectrolRace and Ballot objects are created
        electrol_races = ElectrolRace.objects.filter(tally=self.tally)
        ballots = Ballot.objects.filter(tally=self.tally)
        self.assertGreater(electrol_races.count(), 0)
        self.assertGreater(ballots.count(), 0)

    def test_import_electrol_races_and_ballots_with_exception(self):
        # Prepare test data with faulty file
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballot_order.csv'

        # Call the task with faulty data that raises an exception
        with self.assertRaises(Exception):
            task = async_tsk.delay(tally_id=self.tally.id,
                                   csv_file_path=csv_file_path,)
            task.wait()
