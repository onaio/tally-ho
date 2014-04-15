from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy
from tally_ho.libs.permissions.groups import create_permission_groups


class Command(BaseCommand):
    help = ugettext_lazy("Create groups.")

    def handle(self, *args, **kwargs):
        create_permission_groups()
