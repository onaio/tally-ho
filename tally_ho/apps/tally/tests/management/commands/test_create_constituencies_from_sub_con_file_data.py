import duckdb
from django.test import TestCase

from tally_ho.apps.tally.management.commands.import_electrol_races_and_ballots import (
    async_import_electrol_races_and_ballots_from_ballots_file as async_tsk,
)
from tally_ho.apps.tally.management.commands.import_sub_cons_and_cons import (
    create_constituencies_from_sub_con_file_data,
)
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.libs.tests.test_base import create_tally


class TestCreateConstituenciesFromSubConsFileData(TestCase):
    def setUp(self):
        self.tally = create_tally()
        # Prepare test data
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballots.csv'
        # Create electrol races and balllots
        async_tsk(tally_id=self.tally.id,
                  csv_file_path=csv_file_path,)
        self.duckdb_sub_cons_data = duckdb.from_csv_auto(
            'tally_ho/libs/tests/fixtures/tally_setup_files/subcons.csv',
            header=True)

    def test_create_constituencies(self):
        create_constituencies_from_sub_con_file_data(
            duckdb_sub_con_data=self.duckdb_sub_cons_data,
            tally=self.tally
        )

        # Assert that the Constituency objects are created
        cons = Constituency.objects.filter(tally=self.tally)
        self.assertGreater(cons.count(), 0)

    def test_create_constituencies_with_exception(self):
        file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballot_order.csv'
        # Call the function with faulty data that raises an exception
        self.faulty_duckdb_ballots_data = duckdb.from_csv_auto(
            file_path,
            header=True)
        with self.assertRaises(Exception):
            create_constituencies_from_sub_con_file_data(
                duckdb_sub_con_data=self.faulty_duckdb_ballots_data,
                tally=self.tally
            )
