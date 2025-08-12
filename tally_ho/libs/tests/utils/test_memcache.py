"""Test libs.utils.memcache module."""
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from pymemcache.client.base import PooledClient

from tally_ho.libs.utils.memcache import MemCache


class TestMemCache(TestCase):

    def setUp(self):
        settings.CLIENT_URL = '127.0.0.1:11211'
        self.memcache = MemCache()

    @patch.object(PooledClient, 'set')
    def test_set(self, mock_set):
        key = 'test_key'
        val = 'test_value'
        mock_set.return_value = True
        result, error = self.memcache.set(key, val)
        self.assertTrue(result)
        self.assertIsNone(error)
        mock_set.assert_called_once_with(key, val)

    @patch.object(PooledClient, 'get')
    def test_get(self, mock_get):
        key = 'test_key'
        data = b'test_data'
        mock_get.return_value = data
        result, error = self.memcache.get(key)
        self.assertEqual(result, data.decode('utf-8'))
        self.assertIsNone(error)
        mock_get.assert_called_once_with(key)

    @patch.object(PooledClient, 'incr')
    def test_incr(self, mock_incr):
        key = 'test_key'
        val = 1
        mock_incr.return_value = 2
        result, error = self.memcache.incr(key, val)
        self.assertEqual(result, 2)
        self.assertIsNone(error)
        mock_incr.assert_called_once_with(key, val)

    @patch.object(PooledClient, 'delete')
    def test_delete(self, mock_delete):
        key = 'test_key'
        mock_delete.return_value = True
        result, error = self.memcache.delete(key)
        self.assertTrue(result)
        self.assertIsNone(error)
        mock_delete.assert_called_once_with(key)

    @patch.object(PooledClient, 'set')
    def test_set_exception(self, mock_set):
        key = 'test_key'
        val = 'test_value'
        exception_message = 'Connection error'
        mock_set.side_effect = Exception(exception_message)
        result, error = self.memcache.set(key, val)
        self.assertIsNone(result)
        self.assertEqual(error,
                         str(f'Error setting cache for key {key},'
                             f' error: {exception_message}'))
        mock_set.assert_called_once_with(key, val)

    @patch.object(PooledClient, 'get')
    def test_get_exception(self, mock_get):
        key = 'test_key'
        exception_message = 'Connection error'
        mock_get.side_effect = Exception(exception_message)
        result, error = self.memcache.get(key)
        self.assertIsNone(result)
        self.assertEqual(error,
                         str(f'Error getting cached data for key {key},'
                             f' error: {exception_message}'))
        mock_get.assert_called_once_with(key)

    @patch.object(PooledClient, 'incr')
    def test_incr_exception(self, mock_incr):
        key = 'test_key'
        val = 1
        exception_message = 'Connection error'
        mock_incr.side_effect = Exception(exception_message)
        result, error = self.memcache.incr(key, val)
        self.assertIsNone(result)
        self.assertEqual(error,
                         str(f'Error incrementing cache for key {key},'
                             f' error: {exception_message}'))
        mock_incr.assert_called_once_with(key, val)

    @patch.object(PooledClient, 'delete')
    def test_delete_exception(self, mock_delete):
        key = 'test_key'
        exception_message = 'Connection error'
        mock_delete.side_effect = Exception(exception_message)
        result, error = self.memcache.delete(key)
        self.assertIsNone(result)
        self.assertEqual(error,
                         str(f'Error deleting cache for key {key},'
                             f' error: {exception_message}'))
        mock_delete.assert_called_once_with(key)
