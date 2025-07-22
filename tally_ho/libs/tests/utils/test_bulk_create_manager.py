import json

from django.test import TestCase

from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import create_tally
from tally_ho.libs.utils.memcache import MemCache
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager


class TestBulkCreateManager(TestCase):
    def setUp(self):
        self.tally = create_tally()
        self.objects = []
        for electrol_race_data in electrol_races:
            self.objects.append(
                ElectrolRace(tally=self.tally, **electrol_race_data)
            )
        self.cache_key = "test_cache_key"
        self.memcache_client = MemCache()
        self.memcache_client.delete(self.cache_key)

    def test_bulk_create(self):
        manager = BulkCreateManager(
            objs_count=len(electrol_races),
            cache_instances_count=True,
            cache_key=self.cache_key,
            memcache_client=self.memcache_client,
        )

        # Add objects to the manager
        for obj in self.objects:
            manager.add(obj)

        # Ensure all objects are created
        self.assertEqual(
            ElectrolRace.objects.filter(tally=self.tally).count(),
            len(electrol_races),
        )

        # Ensure cache is updated with the correct count
        memcache_data, _ = self.memcache_client.get(self.cache_key)
        cached_data = json.loads(memcache_data)
        self.assertEqual(
            cached_data.get("elements_processed"), len(electrol_races)
        )
        self.assertTrue(cached_data.get("done"))

    def test_no_cache(self):
        manager = BulkCreateManager(objs_count=len(electrol_races))

        # Add objects to the manager
        for obj in self.objects:
            manager.add(obj)

        # Call the done method to create the remaining objects
        manager.done()

        # Ensure all objects are created
        self.assertEqual(
            ElectrolRace.objects.filter(tally=self.tally).count(),
            len(electrol_races),
        )

    def test_chunk_size(self):
        manager = BulkCreateManager(chunk_size=5)

        # Add objects to the manager
        for obj in self.objects:
            manager.add(obj)

        # Call the done method to create the remaining objects
        manager.done()

        # Ensure all objects are created
        self.assertEqual(
            ElectrolRace.objects.filter(tally=self.tally).count(),
            len(electrol_races),
        )
