#!/usr/bin/env python

import csv
import re

from django.db.utils import IntegrityError
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from optparse import make_option

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


def empty_string_to(value, default):
    return value if len(value) else default


def empty_strings_to_none(row):
    """Convert all empty strings in row to 0."""
    return [empty_string_to(f, None) for f in row]


def invalid_line(row):
    """Ignore lines that are all empty."""
    return len(row) == reduce(lambda x, y: x + 1 if y == '' else 0, row, 0)


def strip_non_numeric(string):
    """Strip non-numerics and safely convert to float.

    :param string: The string to convert.
    :returns: None if string is not a float."""
    try:
        return float(re.sub("[^0-9.]", "", string))
    except ValueError:
        return None


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
                    registrants=empty_string_to(row[5], None),
                    station_number=row[3])

    def import_result_forms(self, result_forms_path):
        with open(result_forms_path, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                row = empty_strings_to_none(row)
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

                try:
                    _, created = ResultForm.objects.get_or_create(
                        barcode=row[7],
                        ballot=ballot,
                        center=center,
                        form_state=FormState.UNSUBMITTED,
                        gender=gender,
                        name=row[4],
                        office=office,
                        serial_number=row[8],
                        station_number=row[2])
                except IntegrityError:
                    pass
