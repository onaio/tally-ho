import json

from django.test import TestCase

from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.tests.test_base import create_tally, create_ballot
from tally_ho.libs.utils.memcache import MemCache
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager
from tally_ho.libs.utils.query_set_helpers import BulkUpdateManyToManyManager
from tally_ho.libs.tests.fixtures.sub_con_data import (
    sub_cons
)

class TestBulkUpdateManyToManyManager(TestCase):
    def setUp(self):
        self.tally = create_tally()
        ballot = create_ballot(self.tally)
        self.many_to_many_fields = { 'ballots': [ballot] }
        self.objects = []
        for sub_con_data in sub_cons:
            self.objects.append(SubConstituency(
                tally=self.tally,
                **sub_con_data
            ))
        # Bulk create sub cons
        manager = BulkCreateManager(
            objs_count=len(sub_cons),
        )
        for obj in self.objects:
            manager.add(obj)
        self.cache_key = 'test_cache_key'
        self.memcache_client = MemCache()
        self.memcache_client.delete(self.cache_key)

    def test_bulk_create(self):
        manager = BulkUpdateManyToManyManager(
            instances_count=len(sub_cons),
            cache_instances_count=True,
            cache_key=self.cache_key,
            memcache_client=self.memcache_client
        )

        # Add objects to the manager
        for obj in self.objects:
            manager.add({
                'instance': obj,
                'many_to_many_fields': self.many_to_many_fields,
            })
        # Ensure all sub con objects have been assigned a ballot
        self.assertEqual(
            SubConstituency.objects.filter(tally=self.tally).values(
                'ballots').count(),
            len(sub_cons))

        # Ensure cache is updated with the correct count
        memcache_data, _ = self.memcache_client.get(self.cache_key)
        cached_data = json.loads(memcache_data)
        self.assertEqual(
            cached_data.get('elements_processed'), len(sub_cons))
        self.assertTrue(cached_data.get('done'))

    def test_no_cache(self):
        manager = BulkUpdateManyToManyManager(instances_count=len(sub_cons))

        # Add objects to the manager
        for obj in self.objects:
            manager.add({
                'instance': obj,
                'many_to_many_fields': self.many_to_many_fields,
            })

        # Call the done method to create the remaining objects
        manager.done()

        # Ensure all sub con objects have been assigned a ballot
        self.assertEqual(
            SubConstituency.objects.filter(tally=self.tally).values(
                'ballots').count(),
            len(sub_cons))

    def test_chunk_size(self):
        manager = BulkUpdateManyToManyManager(chunk_size=5)

        # Add objects to the manager
        for obj in self.objects:
            manager.add({
                'instance': obj,
                'many_to_many_fields': self.many_to_many_fields,
            })

        # Call the done method to create the remaining objects
        manager.done()

        # Ensure all sub con objects have been assigned a ballot
        self.assertEqual(
            SubConstituency.objects.filter(tally=self.tally).values(
                'ballots').count(),
            len(sub_cons))
