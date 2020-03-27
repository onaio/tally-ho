from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError
from django.utils.translation import ugettext_lazy

from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions.groups import GROUPS


def create_user(username, first_name, reset_password=False):
    user, _ = UserProfile.objects.get_or_create(
        username=username,
        first_name=first_name,
        reset_password=False)

    return user


def create_demo_users_with_groups(force=False, password='data'):
    """Create a demo user for each group.

    :param password: The password for the demo users.
    """

    for group in GROUPS:
        obj = Group.objects.get_or_create(name=group)[0]
        username = group.replace(' ', '_').lower()[0:30]
        first_name = group[0:30]

        if force:
            try:
                UserProfile.objects.filter(
                    username=username,
                    first_name=first_name,
                ).delete()
                User.objects.filter(
                    username=username,
                    first_name=first_name,
                ).delete()
            except IntegrityError:
                raise CommandError(
                    'Could not delete existing User or UserProfile for '
                    'username "%s"' % username)

        user = create_user(username, first_name)
        user.set_password(password)
        user.save()
        user.groups.add(obj)


class Command(BaseCommand):
    help = ugettext_lazy("Create demo users with roles/groups.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            help='Force creation of users',
        )

    def handle(self, *args, **options):
        create_demo_users_with_groups(options['force'])
