from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import create_tally,\
    create_constituency, TestBase
from tally_ho.apps.tally.models.constituency import Constituency


class TestConstituency(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self._add_user_to_group(self.user,
                                groups.TALLY_MANAGER)

    def test_constituency(self):
        tally = create_tally()
        tally.users.add(self.user)
        constituency = create_constituency(tally=tally)

        # Test constituency object name is constituency name hyphen center name
        constituency_obj = Constituency.objects.get(pk=constituency.pk)
        expected_object_name = constituency_obj.name
        self.assertEquals(expected_object_name, str(constituency_obj))
