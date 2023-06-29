import json
from django.conf import settings
from pymemcache.client.base import PooledClient

class MemCache(object):
    """
    This helper class is used to create a memcache.
    """

    def __init__(self):
        self.client_url = getattr(settings, 'CLIENT_URL')
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

def cache_model_instances_count_to_memcache(
        cache_key, instances_count, done=False):
    try:
        memcache_client = MemCache()
        cached_data = memcache_client.get(cache_key)[0]
        data = { 'elements_processed': instances_count, 'done': done }
        if cached_data:
            current_elements_processed =\
                json.loads(cached_data).get('elements_processed')
            data['elements_processed'] =\
                instances_count + current_elements_processed
            memcache_client.set(cache_key, json.dumps(data))
        else:
            memcache_client.set(cache_key, json.dumps(data))
        return
    except Exception as e:
        msg = 'Error caching instances count, error: %s' % e
        raise Exception(msg)
