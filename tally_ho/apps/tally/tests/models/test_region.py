from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_office,\
    create_tally, create_region, TestBase
from tally_ho.apps.tally.models.region import Region


class TestRegion(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user,
                                groups.TALLY_MANAGER)

    def test_region(self):
        tally = create_tally()
        tally.users.add(self.user)

        office = create_office(tally=tally)
        region = create_region(office=office, tally=tally)

        # Test region object name is region name hyphen office name
        region_obj = Region.objects.get(pk=region.pk)
        expected_object_name =\
            f'{region_obj.name} - {office.name}'
        self.assertEquals(expected_object_name, str(region_obj))
