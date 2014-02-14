from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy
from libya_tally.libs.reports import print_total_result_form_report


class Command(BaseCommand):
    help = ugettext_lazy("Create demo users with roles/groups.")

    def handle(self, *args, **kwargs):
        print_total_result_form_report()
