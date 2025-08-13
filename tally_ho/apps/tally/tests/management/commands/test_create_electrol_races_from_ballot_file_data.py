import duckdb
from django.conf import settings
from django.test import TestCase

from tally_ho.apps.tally.management.commands.import_electrol_races_and_ballots import (
    create_electrol_races_from_ballot_file_data,
)
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.libs.tests.test_base import create_tally


class TestCreateElectrolRacesFromBallotFileData(TestCase):
    def setUp(self):
        self.tally = create_tally()
        col_names_to_model_field_map =\
            settings.BALLOT_COLS_TO_ELECTROL_RACE_MODEL_FIELDS_MAPPING
        electrol_races_cols_list =\
            list(col_names_to_model_field_map.keys())
        self.duckdb_ballots_data = duckdb.from_csv_auto(
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballots.csv',
            header=True).project(
            ','.join(electrol_races_cols_list)).distinct()

    def test_create_electrol_races(self):
        create_electrol_races_from_ballot_file_data(
            duckdb_ballots_data=self.duckdb_ballots_data,
            tally=self.tally
        )

        # Assert that the ElectrolRace objects are created
        electrol_races = ElectrolRace.objects.filter(tally=self.tally)
        self.assertEqual(electrol_races.count(),
                         self.duckdb_ballots_data.shape[0])

    def test_create_electrol_races_with_exception(self):
        file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballot_order.csv'
        # Call the function with faulty data that raises an exception
        self.faulty_duckdb_ballots_data = duckdb.from_csv_auto(
            file_path,
            header=True)
        with self.assertRaises(Exception):
            create_electrol_races_from_ballot_file_data(
                duckdb_ballots_data=self.faulty_duckdb_ballots_data,
                tally=self.tally
            )
