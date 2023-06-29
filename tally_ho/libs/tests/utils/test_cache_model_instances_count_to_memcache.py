from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.conf import settings

from tally_ho.libs.utils.cache_model_instances_count_to_memcache import (
    cache_model_instances_count_to_memcache
)
from tally_ho.libs.utils.memcache import MemCache

class TestCacheModelInstancesCount(TestCase):

    def setUp(self):
        settings.CLIENT_URL = '127.0.0.1:11211'
        self.memcache = MemCache()
        self.cache_key = 'test_cache_key'
        self.memcache.delete(self.cache_key)

    @patch('tally_ho.libs.utils.memcache.MemCache', autospec=True)
    def test_cache_model_instances_count_to_memcache(self, mock_memcache):
        instances_count = 10
        done = False

        # Mock the MemCache instance
        memcache_instance = MagicMock()
        mock_memcache.return_value = memcache_instance

        # Test case 1: Cached data exists
        memcache_instance.get.return_value =\
            ('{"elements_processed": 5, "done": true}', None)
        cache_model_instances_count_to_memcache(self.cache_key,
                                                instances_count,
                                                done,
                                                memcache_client=
                                                memcache_instance)
        memcache_instance.get.assert_called_once_with(self.cache_key)
        memcache_instance.set.assert_called_once_with(
            self.cache_key, '{"elements_processed": 15, "done": false}')

        # Test case 2: Cached data does not exist
        memcache_instance.get.return_value = (None, None)
        cache_model_instances_count_to_memcache(self.cache_key,
                                                instances_count,
                                                done,
                                                memcache_client=
                                                memcache_instance)
        memcache_instance.get.assert_called_with(self.cache_key)
        memcache_instance.set.assert_called_with(
            self.cache_key, '{"elements_processed": 10, "done": false}')

        # Test case 3: Exception raised
        memcache_instance.get.side_effect = Exception('Connection error')
        with self.assertRaises(Exception) as context:
            cache_model_instances_count_to_memcache(self.cache_key,
                                                    instances_count,
                                                    done,
                                                    memcache_client=
                                                    memcache_instance)
        self.assertEqual(
            str(context.exception),
            'Error caching instances count, error: Connection error')
