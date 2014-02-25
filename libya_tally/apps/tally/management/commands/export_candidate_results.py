from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from libya_tally.libs.views.exports import export_candidate_votes


class Command(BaseCommand):
    help = ugettext_lazy("Export candidate votes list.")

    def handle(self, *args, **kwargs):
        export_candidate_votes()
