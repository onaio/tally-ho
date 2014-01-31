#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8

import csv
import re

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from libya_tally.apps.tally.models.candidate import Candidate
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.station import Station
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.enums.center_type import CenterType
from libya_tally.libs.models.enums.gender import Gender
from libya_tally.libs.models.enums.race_type import RaceType

CANDIDATES_PATH = 'data/candidates.csv'
CENTERS_PATH = 'data/centers.csv'
STATIONS_PATH = 'data/stations.csv'
SUB_CONSTITUENCIES_PATH = 'data/sub_constituencies.csv'

SPECIAL_VOTING = 'Special Voting'


def empty_string_to(value, default):
    return value if len(value) else default


def empty_strings_to_zero(row):
    """Convert all empty strings in row to 0."""
    return [empty_string_to(f, 0) for f in row]


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

    def handle(self, *args, **kwargs):
        self.import_sub_constituencies()
        self.import_centers()
        self.import_stations()
        self.import_candidates()

    def import_sub_constituencies(self):
        with open(SUB_CONSTITUENCIES_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                if invalid_line(row):
                    next

                row = empty_strings_to_zero(row)

                try:
                    code_value = int(row[0])

                    _, created = SubConstituency.objects.get_or_create(
                        code=code_value,
                        field_office=row[1],
                        races=row[2],
                        ballot_number_general=row[3],
                        ballot_number_women=row[4],
                        number_of_ballots=row[5],
                        component_ballot=row[6])
                except ValueError:
                    pass

    def import_centers(self):
        with open(CENTERS_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                if not invalid_line(row):
                    sc_code = row[6]
                    sub_constituency = None

                    if sc_code == SPECIAL_VOTING:
                        center_type = CenterType.SPECIAL
                    else:
                        sc_code = int(row[6])
                        sub_constituency = SubConstituency.objects.get(
                            code=sc_code)
                        center_type = CenterType.GENERAL

                    _, created = Center.objects.get_or_create(
                        region=row[1],
                        code=row[2],
                        office=row[4],
                        sub_constituency=sub_constituency,
                        name=row[8],
                        mahalla=row[9],
                        village=row[10],
                        center_type=center_type,
                        longitude=strip_non_numeric(row[12]),
                        latitude=strip_non_numeric(row[13]))

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

                # ensure that SC is converted to a number
                sc_code = int(float(row[2]))

                try:
                    sub_constituency = SubConstituency.objects.get(
                        code=sc_code)
                except SubConstituency.DoesNotExist:
                    print('[WARNING] SubConstituency "%s" does not exist' %
                          sc_code)

                gender = getattr(Gender, row[4].upper())

                _, created = Station.objects.get_or_create(
                    center=center,
                    sub_constituency=sub_constituency,
                    gender=gender,
                    registrants=empty_string_to(row[5], None),
                    station_number=row[3])

    def import_candidates(self):
        with open(CANDIDATES_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                race_code = row[18]

                race_type = {
                    0: RaceType.GENERAL,
                    1: RaceType.WOMEN,
                    2: RaceType.COMPONENT_AMAZIGH,
                    3: RaceType.COMPONENT_TWARAG,
                    4: RaceType.COMPONENT_TEBU
                }[int(race_code)]

                sc_code = row[7]

                try:
                    sub_constituency = SubConstituency.objects.get(
                        code=sc_code)
                except SubConstituency.DoesNotExist:
                    print('[WARNING] SubConstituency "%s" does not exist' %
                          sc_code)

                _, created = Candidate.objects.get_or_create(
                    full_name=row[14],
                    race_type=race_type,
                    sub_constituency=sub_constituency)
