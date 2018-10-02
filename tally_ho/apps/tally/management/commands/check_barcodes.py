#!/usr/bin/env python

import csv

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from tally_ho.apps.tally.management.commands import import_data
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.result_form import ResultForm


RESULT_FORMS_PATH = 'data/result_forms.csv'


class Command(BaseCommand):
    help = ugettext_lazy('Check that the centers and stations assigned to '
                         'result forms in the system match those in the raw '
                         'data.')

    def handle(self, *args, **kwargs):
        self.check_result_forms()

    def check_result_forms(self):
        with open(RESULT_FORMS_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                row = import_data.empty_strings_to_none(row)
                barcode = row[7]
                code = row[1]

                try:
                    Center.objects.get(code=code)
                except Center.DoesNotExist:
                    continue
                else:
                    code = int(code)

                ballot = int(row[0])
                station_number = int(row[2])

                result_form = ResultForm.objects.get(barcode=barcode)

                if result_form.center.code != code or\
                        result_form.station_number != station_number or\
                        result_form.ballot.number != ballot:
                    self.stdout.write(self.style.NOTICE(
                        '%s system center %s~=%s station %s~=%s ballot %s~=%s'
                        % (barcode, result_form.center.code, code,
                           result_form.station_number, station_number,
                           result_form.ballot.number, ballot)))
