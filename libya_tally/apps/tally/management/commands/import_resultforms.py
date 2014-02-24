#!/usr/bin/env python

import csv

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from optparse import make_option

import libya_tally.apps.tally.management.commands.import_data as imp
from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.office import Office
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.gender import Gender

STATIONS_PATH = 'data/stations.csv'
RESULT_FORMS_PATH = 'data/new_result_forms.csv'


class Command(BaseCommand):
    help = ugettext_lazy("Import polling data.")
    option_list = BaseCommand.option_list + (
        make_option('--result-forms-path'),
    )

    def handle(self, *args, **options):
        result_path = options.get('result_forms_path')
        result_path = result_path \
            if result_path is not None else RESULT_FORMS_PATH

        print '[INFO] import result forms'
        self.import_result_forms(result_path)

    def import_result_forms(self, result_forms_path):
        replacement_count = 0

        with open(result_forms_path, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                row = imp.empty_strings_to_none(row)
                ballot = Ballot.objects.get(number=row[0])
                barcode = row[7]

                center = None
                gender = None

                try:
                    center = Center.objects.get(
                        code=row[1])
                    gender = getattr(Gender, row[3].upper())
                except Center.DoesNotExist:
                    pass

                office_name = row[5]
                office = None

                if office_name:
                    try:
                        office = Office.objects.get(name=office_name.strip())
                    except Office.DoesNotExist:
                        print('[WARNING] Office "%s" does not exist' %
                              office_name)

                is_replacement = True if center is None else False

                if is_replacement:
                    replacement_count += 1

                kwargs = {
                    'barcode': barcode,
                    'ballot': ballot,
                    'center': center,
                    'gender': gender,
                    'name': row[4],
                    'office': office,
                    'serial_number': row[8],
                    'station_number': row[2],
                    'form_state': FormState.UNSUBMITTED,
                    'is_replacement': is_replacement
                }

                try:
                    form = ResultForm.objects.get(barcode=barcode)
                    print '[INFO] Found with barcode: %s' % barcode
                except ResultForm.DoesNotExist:
                    print '[INFO] Create with barcode: %s' % barcode
                    ResultForm.objects.create(**kwargs)
                else:
                    if is_replacement:
                        form.is_replacement = is_replacement
                        form.save()

        print '[INFO] Number of replacement forms: %s' % replacement_count
