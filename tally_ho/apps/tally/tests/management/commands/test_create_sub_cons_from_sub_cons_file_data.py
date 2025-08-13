import json
from unittest.mock import MagicMock, patch

import duckdb
from django.test import TestCase

from tally_ho.apps.tally.management.commands.import_electrol_races_and_ballots import (
    async_import_electrol_races_and_ballots_from_ballots_file as async_tsk,
)
from tally_ho.apps.tally.management.commands.import_sub_cons_and_cons import (
    create_constituencies_from_sub_con_file_data,
    create_sub_constituencies_from_sub_con_file_data,
)
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.tests.test_base import create_tally


class TestCreateSubConsFromSubConsFileData(TestCase):
    def setUp(self):
        self.tally = create_tally()
        csv_file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballots.csv'
        # Create electrol races and balllots
        async_tsk(tally_id=self.tally.id,
                  csv_file_path=csv_file_path,)
        self.duckdb_sub_cons_data = duckdb.from_csv_auto(
            'tally_ho/libs/tests/fixtures/tally_setup_files/subcons.csv',
            header=True)
        # Create constituencies
        create_constituencies_from_sub_con_file_data(
            duckdb_sub_con_data=self.duckdb_sub_cons_data,
            tally=self.tally
        )
        self.cache_key = 'test_cache_key'

    @patch('tally_ho.libs.utils.memcache.MemCache', autospec=True)
    def test_create_sub_constituencies(self, mock_memcache):
        constituencies_by_name =\
                {
                    constituency.name:\
                    constituency for constituency in\
                        Constituency.objects.filter(tally=self.tally)
                }
        # Mock the MemCache instance
        memcache_instance = MagicMock()
        mock_memcache.return_value = memcache_instance
        memcache_instance.get.return_value = (None, None)

        create_sub_constituencies_from_sub_con_file_data(
            duckdb_sub_con_data=self.duckdb_sub_cons_data,
            constituencies_by_name=constituencies_by_name,
            tally=self.tally,
            instances_count_memcache_key=self.cache_key,
            memcache_client=memcache_instance
        )

        cached_data =\
            json.dumps(
                {
                    "elements_processed": self.duckdb_sub_cons_data.shape[0],
                    "done": True
                }
            )
        memcache_instance.get.assert_called_once_with(self.cache_key)
        memcache_instance.set.assert_called_once_with(
            self.cache_key,
            cached_data)

        # Assert that the Sub Constituency objects are created
        cons = SubConstituency.objects.filter(tally=self.tally)
        self.assertGreater(cons.count(), 0)

    @patch('tally_ho.libs.utils.memcache.MemCache', autospec=True)
    def test_create_sub_constituencies_with_exception(self, mock_memcache):
        file_path =\
            'tally_ho/libs/tests/fixtures/tally_setup_files/ballot_order.csv'
        # Call the function with faulty data that raises an exception
        faulty_duckdb_ballots_data = duckdb.from_csv_auto(
            file_path,
            header=True)
        constituencies_by_name =\
                {
                    constituency.name:\
                    constituency for constituency in\
                        Constituency.objects.filter(tally=self.tally)
                }
        # Mock the MemCache instance
        memcache_instance = MagicMock()
        mock_memcache.return_value = memcache_instance
        memcache_instance.get.return_value = (None, None)

        with self.assertRaises(Exception):
            create_sub_constituencies_from_sub_con_file_data(
            duckdb_sub_con_data=faulty_duckdb_ballots_data,
            constituencies_by_name=constituencies_by_name,
            tally=self.tally,
            instances_count_memcache_key=self.cache_key,
            memcache_client=memcache_instance
        )
