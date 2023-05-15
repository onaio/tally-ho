from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy

from tally_ho.libs.views.exports import export_candidate_votes


class Command(BaseCommand):
    help = gettext_lazy("Export candidate votes list.")

    def handle(self, *args, **kwargs):
        export_candidate_votes(save_barcodes=True, output_duplicates=True)
        export_candidate_votes(save_barcodes=False, output_duplicates=False,
                               show_disabled_candidates=False)
