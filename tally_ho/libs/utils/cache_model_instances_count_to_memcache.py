import json

def cache_model_instances_count_to_memcache(
        cache_key, instances_count, done=False, memcache_client=None):
    try:
        cached_data, _ = memcache_client.get(cache_key)
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
