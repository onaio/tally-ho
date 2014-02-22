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
from libya_tally.apps.tally.models.station import Station
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.gender import Gender

STATIONS_PATH = 'data/stations.csv'
RESULT_FORMS_PATH = 'data/result_forms.csv'


class Command(BaseCommand):
    help = ugettext_lazy("Import polling data.")
    option_list = BaseCommand.option_list + (
        make_option('--result-forms-path'),
    )

    def handle(self, *args, **options):
        result_path = options.get('result_forms_path')
        result_path = result_path \
            if result_path is not None else RESULT_FORMS_PATH

        print '[INFO] import stations'
        self.import_stations()

        print '[INFO] import result forms'
        self.import_result_forms(result_path)

    def import_stations(self):
        with open(STATIONS_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                center_code = row[0]

                try:
                    center = Center.objects.get(code=center_code)
                except Center.DoesNotExist:
                    center, created = Center.objects.get_or_create(
                        code=center_code,
                        name=row[1])

                try:
                    # attempt to convert SC to a number
                    sc_code = int(float(row[2]))
                    sub_constituency = SubConstituency.objects.get(
                        code=sc_code)
                except (SubConstituency.DoesNotExist, ValueError):
                    print('[WARNING] SubConstituency "%s" does not exist' %
                          sc_code)

                gender = getattr(Gender, row[4].upper())

                _, created = Station.objects.get_or_create(
                    center=center,
                    sub_constituency=sub_constituency,
                    gender=gender,
                    registrants=imp.empty_string_to(row[5], None),
                    station_number=row[3])

    def import_result_forms(self, result_forms_path):
        replacement_count = 0

        with open(result_forms_path, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                row = imp.empty_strings_to_none(row)
                ballot = Ballot.objects.get(number=row[0])

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
                    'barcode': row[7],
                    'ballot': ballot,
                    'center': center,
                    'gender': gender,
                    'name': row[4],
                    'office': office,
                    'serial_number': row[8],
                    'station_number': row[2]
                }

                try:
                    form = ResultForm.objects.get(**kwargs)
                except ResultForm.DoesNotExist:
                    kwargs['form_state'] = FormState.UNSUBMITTED
                    kwargs['is_replacement'] = is_replacement
                    ResultForm.objects.create(**kwargs)
                else:
                    if is_replacement:
                        form.is_replacement = is_replacement
                        form.save()

        print '[INFO] Number of replacement forms: %s' % replacement_count
