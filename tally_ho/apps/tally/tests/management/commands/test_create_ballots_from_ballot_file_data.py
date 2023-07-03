import duckdb
import json

from django.conf import settings
from django.test import TestCase
from unittest.mock import patch, MagicMock

from tally_ho.apps.tally.management.commands.import_electrol_races_and_ballots\
    import (
        create_electrol_races_from_ballot_file_data,
        create_ballots_from_ballot_file_data
    )
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.libs.tests.test_base import create_tally

class TestCreateBallotsFromBallotFileData(TestCase):
    def setUp(self):
        self.tally = create_tally()
        self.duckdb_ballots_data = duckdb.from_csv_auto(
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballots.csv',
            header=True).distinct()
        col_names_to_model_field_map =\
            getattr(settings,
                    'BALLOT_COLS_TO_ELECTROL_RACE_MODEL_FIELDS_MAPPING')
        electrol_races_cols_list =\
            list(col_names_to_model_field_map.keys())
        self.duckdb_electrol_races_ballots_data =\
            self.duckdb_ballots_data.project(
            ','.join(electrol_races_cols_list)).distinct()
        create_electrol_races_from_ballot_file_data(
            duckdb_ballots_data=self.duckdb_electrol_races_ballots_data,
            tally=self.tally
        )
        self.cache_key = 'test_cache_key'

    @patch('tally_ho.libs.utils.memcache.MemCache', autospec=True)
    def test_create_ballots(self, mock_memcache):
        electrol_races = ElectrolRace.objects.filter(tally=self.tally)
        # Mock the MemCache instance
        memcache_instance = MagicMock()
        mock_memcache.return_value = memcache_instance
        memcache_instance.get.return_value = (None, None)

        create_ballots_from_ballot_file_data(
            duckdb_ballots_data=self.duckdb_ballots_data,
            electrol_races=electrol_races,
            tally=self.tally,
            instances_count_memcache_key=self.cache_key,
            memcache_client=memcache_instance
        )
        ballot_name_column_name =\
            getattr(settings,
                    'BALLOT_NAME_COLUMN_NAME_IN_BALLOT_FILE')
        self.duckdb_ballots_data =\
            self.duckdb_ballots_data.project(ballot_name_column_name).filter(
                str(f"{ballot_name_column_name} != "
                    "'ballot_number_senate_general - Matrix'"
                    f" and {ballot_name_column_name} != "
                    "'ballot_number_senate_women - Matrix'"
                    f" and {ballot_name_column_name} != "
                    "'ballot_number_HOR_women - Matrix' and "
                    f"{ballot_name_column_name} != "
                    f"'ballot_number_HOR_component - Matrix'")).distinct()

        cached_data =\
            json.dumps(
                {
                    "elements_processed": self.duckdb_ballots_data.shape[0],
                    "done": True
                }
            )
        memcache_instance.get.assert_called_once_with(self.cache_key)
        memcache_instance.set.assert_called_once_with(
            self.cache_key,
            cached_data)

        # Assert that the Ballot objects are created
        self.assertEqual(Ballot.objects.filter(tally=self.tally).count(),
                         self.duckdb_ballots_data.shape[0])

    @patch('tally_ho.libs.utils.memcache.MemCache', autospec=True)
    def test_create_ballots_with_exception(self, mock_memcache):
        file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballot_order.csv'
        # Call the function with faulty data that raises an exception
        faulty_duckdb_ballots_data = duckdb.from_csv_auto(
            file_path,
            header=True)
        electrol_races = ElectrolRace.objects.filter(tally=self.tally)
        # Mock the MemCache instance
        memcache_instance = MagicMock()
        mock_memcache.return_value = memcache_instance
        memcache_instance.get.return_value = (None, None)

        with self.assertRaises(Exception):
            create_ballots_from_ballot_file_data(
                duckdb_ballots_data=faulty_duckdb_ballots_data,
                electrol_races=electrol_races,
                tally=self.tally,
                instances_count_memcache_key=self.cache_key,
                memcache_client=memcache_instance
            )
