from tally_ho.libs.tests.test_base import TestBase, create_tally
from django.contrib.auth.models import Group
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.forms.edit_user_profile_form import (
    EditUserProfileForm,
    EditAdminProfileForm,
    EditTallyManagerProfileForm,
)


class EditUserProfileFormTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

    def test_blank_data(self):
        """
        Test that blank validation errors are triggered when no data is
        provided.
        """
        form = EditUserProfileForm({})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'username': ['This field is required.'],
             'group': ['This field is required.']})

    def test_dupliate_username_error(self):
        """
        Test that duplicate username error is trigger when similar usernames
        are entered.
        """
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
        """
        Test that data is saved successfully when valid data is passed.
        """
        group = Group.objects.get(name='Quality Control Supervisor')
        username = 'john_doe'
        form =\
            EditUserProfileForm({'username': username, 'group': group.id})
        self.assertTrue(form.is_valid())
        form.save()
        user = UserProfile.objects.filter(username=username)
        self.assertEqual(user.count(), 1)


class EditAdminProfileFormTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally = create_tally()

    def test_blank_data(self):
        """
        Test that blank validation errors are triggered when no data is
        provided.
        """
        form = EditAdminProfileForm({})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'username': ['This field is required.']})

    def test_valid_data_creates_super_admin(self):
        """
        Test that a user is created with SUPER_ADMINISTRATOR group.
        """
        username = 'admin_user'
        form = EditAdminProfileForm({
            'username': username,
            'first_name': 'Admin',
            'last_name': 'User',
            'email': 'admin@example.com',
            'administrated_tallies': [self.tally.id],
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, username)
        self.assertTrue(
            user.groups.filter(name=groups.SUPER_ADMINISTRATOR).exists())
        self.assertIn(self.tally, user.administrated_tallies.all())

    def test_password_set_to_username_on_create(self):
        """
        Test that password is set to username when creating a new admin.
        """
        username = 'new_admin'
        form = EditAdminProfileForm({
            'username': username,
            'administrated_tallies': [self.tally.id],
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.check_password(username))
        self.assertTrue(user.reset_password)

    def test_reset_password_on_edit(self):
        """
        Test that password is reset when reboot_password is checked.
        """
        admin = UserProfile.objects.create(username='admin_reset')
        admin.set_password('oldpassword')
        admin.save()
        admin_group = Group.objects.get(name=groups.SUPER_ADMINISTRATOR)
        admin.groups.add(admin_group)

        form = EditAdminProfileForm({
            'username': 'admin_reset',
            'reboot_password': True,
        }, instance=admin)
        self.assertTrue(form.is_valid())
        updated_user = form.save()
        self.assertTrue(updated_user.check_password('admin_reset'))
        self.assertTrue(updated_user.reset_password)


class EditTallyManagerProfileFormTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally = create_tally()
        self.tally2 = create_tally(name="secondTally")

    def test_blank_data(self):
        """
        Test that blank validation errors are triggered when no data is
        provided.
        """
        form = EditTallyManagerProfileForm({})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'username': ['This field is required.']})

    def test_valid_data_creates_tally_manager(self):
        """
        Test that a user is created with TALLY_MANAGER group.
        """
        username = 'tally_manager_user'
        form = EditTallyManagerProfileForm({
            'username': username,
            'first_name': 'Tally',
            'last_name': 'Manager',
            'email': 'tallymanager@example.com',
            'administrated_tallies': [self.tally.id],
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, username)
        self.assertTrue(
            user.groups.filter(name=groups.TALLY_MANAGER).exists())
        # Should not be in SUPER_ADMINISTRATOR group
        self.assertFalse(
            user.groups.filter(name=groups.SUPER_ADMINISTRATOR).exists())
        self.assertIn(self.tally, user.administrated_tallies.all())

    def test_password_set_to_username_on_create(self):
        """
        Test that password is set to username when creating a new tally
        manager.
        """
        username = 'new_tally_manager'
        form = EditTallyManagerProfileForm({
            'username': username,
            'administrated_tallies': [self.tally.id],
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.check_password(username))
        self.assertTrue(user.reset_password)

    def test_multiple_tallies_assignment(self):
        """
        Test that multiple tallies can be assigned to a tally manager.
        """
        username = 'multi_tally_manager'
        form = EditTallyManagerProfileForm({
            'username': username,
            'administrated_tallies': [self.tally.id, self.tally2.id],
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.administrated_tallies.count(), 2)
        self.assertIn(self.tally, user.administrated_tallies.all())
        self.assertIn(self.tally2, user.administrated_tallies.all())

    def test_edit_existing_tally_manager(self):
        """
        Test editing an existing tally manager updates user info
        and keeps them in TALLY_MANAGER group.
        """
        # Create a tally manager first
        tm = UserProfile.objects.create(username='existing_tm')
        tm.set_password('oldpassword')
        tm.save()
        tm_group = Group.objects.get(name=groups.TALLY_MANAGER)
        tm.groups.add(tm_group)

        # Edit the tally manager
        form = EditTallyManagerProfileForm({
            'username': 'existing_tm',
            'first_name': 'Updated',
            'last_name': 'TallyManager',
        }, instance=tm)
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'TallyManager')
        # Should still be in TALLY_MANAGER group
        self.assertTrue(
            updated_user.groups.filter(name=groups.TALLY_MANAGER).exists())

    def test_reset_password_on_edit(self):
        """
        Test that password is reset when reboot_password is checked.
        """
        tm = UserProfile.objects.create(username='tm_reset')
        tm.set_password('oldpassword')
        tm.save()
        tm_group = Group.objects.get(name=groups.TALLY_MANAGER)
        tm.groups.add(tm_group)

        form = EditTallyManagerProfileForm({
            'username': 'tm_reset',
            'reboot_password': True,
        }, instance=tm)
        self.assertTrue(form.is_valid())
        updated_user = form.save()
        self.assertTrue(updated_user.check_password('tm_reset'))
        self.assertTrue(updated_user.reset_password)

    def test_groups_cleared_and_reassigned(self):
        """
        Test that when saving, existing groups are cleared and only
        TALLY_MANAGER is assigned.
        """
        # Create user with multiple groups
        user = UserProfile.objects.create(username='multi_group_user')
        user.groups.add(Group.objects.get(name=groups.SUPER_ADMINISTRATOR))
        user.groups.add(Group.objects.get(name=groups.TALLY_MANAGER))
        self.assertEqual(user.groups.count(), 2)

        form = EditTallyManagerProfileForm({
            'username': 'multi_group_user',
        }, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        # Should only have TALLY_MANAGER group now
        self.assertEqual(updated_user.groups.count(), 1)
        self.assertTrue(
            updated_user.groups.filter(name=groups.TALLY_MANAGER).exists())

    def test_duplicate_username_error(self):
        """
        Test that duplicate username error is triggered when similar usernames
        are entered.
        """
        username = 'tally_mgr'
        form1 = EditTallyManagerProfileForm({
            'username': username,
            'administrated_tallies': [self.tally.id],
        })
        self.assertTrue(form1.is_valid())
        form1.save()

        form2 = EditTallyManagerProfileForm({
            'username': 'Tally_Mgr',  # Same username, different case
            'administrated_tallies': [self.tally.id],
        })
        self.assertFalse(form2.is_valid())
        self.assertEqual(
            form2.errors,
            {'username': ['A user with that username already exists.']})
