from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy
from tally_system.libs.verify.quarantine_checks import create_quarantine_checks


class Command(BaseCommand):
    help = ugettext_lazy("Create demo users with roles/groups.")

    def handle(self, *args, **kwargs):
        create_quarantine_checks()
