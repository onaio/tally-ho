from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy
from tally_ho.libs.verify.quarantine_checks import create_quarantine_checks
from tally_ho.apps.tally.models.tally import Tally


class Command(BaseCommand):
    help = gettext_lazy("Create quarantine checks for a specific tally.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--tally-id",
            type=int,
            required=True,
            help="Tally ID to create quarantine checks for",
        )

    def handle(self, *args, **options):
        tally_id = options["tally_id"]

        # Validate that tally exists
        try:
            Tally.objects.get(id=tally_id)
        except Tally.DoesNotExist:
            raise CommandError(f"Tally with id {tally_id} does not exist")

        create_quarantine_checks(tally_id=tally_id)