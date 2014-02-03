from django.contrib.auth.models import User, Group, AnonymousUser

from django.test import TestCase
from django.test import RequestFactory

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.permissions.groups import create_permission_groups, \
    add_user_to_group


def create_result_form(barcode='123456789', form_state=FormState.UNSUBMITTED):
    ballot, _ = Ballot.objects.get_or_create(number=1,
                                             race_type=RaceType.GENERAL)
    result_form, _ = ResultForm.objects.get_or_create(
        ballot=ballot,
        barcode=barcode,
        serial_number=0,
        form_state=form_state)

    return result_form


class TestBase(TestCase):
    @classmethod
    def _create_user(cls, username='bob', password='bob'):
        return User.objects.create(username=username, password=password)

    @classmethod
    def _get_request(cls, user=None):
        request = RequestFactory().get('/')
        request.user = user \
            if user is not None and isinstance(user, User) else AnonymousUser()
        return request

    def _create_and_login_user(self, username='bob', password='bob'):
        self.user = self._create_user(username, password)
        # to simulate login, assing user to a request object
        request = RequestFactory().get('/')
        request.user = self.user
        self.request = request

    def _create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, 13)

    def _add_user_to_group(self, user, name):
        if Group.objects.count() == 0:
            self._create_permission_groups()
        count = user.groups.count()
        add_user_to_group(user, name)
        self.assertTrue(user.groups.count() > count)
