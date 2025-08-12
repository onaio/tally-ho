from django.conf import settings
from pymemcache.client.base import PooledClient


class MemCache:
    """
    This helper class is used to create a memcache.
    """

    def __init__(self):
        self.client_url = settings.CLIENT_URL
        self.client = self._set_client()

    def _set_client(self):
        try:
            return PooledClient(self.client_url, max_pool_size=10)
        except Exception as e:
            msg = f'Error creating memcache client, error: {e}'
            raise Exception(msg)

    def set(self, key, val):
        try:
            return self.client.set(key, val), None
        except Exception as e:
            msg = f'Error setting cache for key {key}, error: {e}'
            return None, msg

    def get(self, key):
        try:
            data = self.client.get(key)
            return data.decode("utf-8") if data else None, None
        except Exception as e:
            msg = f'Error getting cached data for key {key}, error: {e}'
            return None, msg

    def incr(self, key, val):
        try:
            return self.client.incr(key, val), None
        except Exception as e:
            msg = f'Error incrementing cache for key {key}, error: {e}'
            return None, msg

    def delete(self, key):
        try:
            return self.client.delete(key), None
        except Exception as e:
            msg = f'Error deleting cache for key {key}, error: {e}'
            return None, msg
