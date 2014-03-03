from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy
from tally_system.libs.permissions.groups import create_demo_users_with_groups


class Command(BaseCommand):
    help = ugettext_lazy("Create demo users with roles/groups.")

    def handle(self, *args, **kwargs):
        create_demo_users_with_groups()
