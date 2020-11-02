from tally_ho.libs.tests.test_base import TestBase
from django.contrib.auth.models import Group
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditUserProfileForm
)


class EditUserProfileFormTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

    def test_blank_data(self):
        form = EditUserProfileForm({})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'username': ['This field is required.'],
             'group': ['This field is required.']})

    def test_dupliate_username_error(self):
        username = 'john_doe'
        group = Group.objects.get(name='Quality Control Supervisor')
        old_form =\
            EditUserProfileForm({'username': username, 'group': group.id})
        self.assertTrue(old_form.is_valid())
        old_form.save()
        new_form =\
            EditUserProfileForm({'username': 'John_Doe', 'group': group.id})
        self.assertFalse(new_form.is_valid())
        self.assertEqual(
            new_form.errors,
            {'username': ['A user with that username already exists.']})

    def test_valid_data(self):
        group = Group.objects.get(name='Quality Control Supervisor')
        username = 'john_doe'
        form =\
            EditUserProfileForm({'username': username, 'group': group.id})
        self.assertTrue(form.is_valid())
        form.save()
        user = UserProfile.objects.filter(username=username)
        self.assertEqual(user.count(), 1)
