from django.test import TransactionTestCase
from celery.contrib.testing.worker import start_worker

from tally_ho.apps.tally.management.commands.import_electrol_races_and_ballots\
    import (
        async_import_electrol_races_and_ballots_from_ballots_file as\
            async_impt_electrol_races_ballots_tsk,
    )
from tally_ho.apps.tally.management.commands.import_sub_cons_and_cons\
    import (
        async_import_sub_constituencies_and_constituencies_from_sub_cons_file\
            as async_impt_sub_cons_and_cons_tsk,
    )
from tally_ho.apps.tally.management.commands.asign_ballots_to_sub_cons\
    import async_asign_ballots_to_sub_cons_from_ballots_file
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.tests.test_base import create_tally
from tally_ho.celeryapp import app

class AsyncAssignBallotsToSubConsTestCase(TransactionTestCase):
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

    def test_async_assign_ballots_to_sub_cons(self):
        # Prepare test data
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/subs_ballots.csv'
        task = async_asign_ballots_to_sub_cons_from_ballots_file.delay(
                        tally_id=self.tally.id,
                        csv_file_path=csv_file_path,)
        task.wait()

        # Assert that the SubConstituency Ballots objects are created
        sub_cons = SubConstituency.objects.filter(tally=self.tally)
        self.assertGreater(
            len([sub_con.ballots.all().count() for sub_con in sub_cons]), 0)

    def test_async_assign_ballots_to_sub_cons_with_exception(self):
        # Prepare test data with faulty file
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballot_order.csv'

        # Call the task with faulty data that raises an exception
        with self.assertRaises(Exception):
            task = async_asign_ballots_to_sub_cons_from_ballots_file.delay(
                        tally_id=self.tally.id,
                        csv_file_path=csv_file_path,)
            task.wait()
