#!/usr/bin/env python

import csv
import re

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.candidate import Candidate
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.apps.tally.models.station import Station
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.enums.center_type import CenterType
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.gender import Gender
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.permissions.groups import create_permission_groups

BALLOT_ORDER_PATH = 'data/ballot_order.csv'
CANDIDATES_PATH = 'data/candidates.csv'
CENTERS_PATH = 'data/centers.csv'
RESULT_FORMS_PATH = 'data/result_forms.csv'
STATIONS_PATH = 'data/stations.csv'
SUB_CONSTITUENCIES_PATH = 'data/sub_constituencies.csv'

SPECIAL_VOTING = 'Special Voting'


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

    def handle(self, *args, **kwargs):
        print '[INFO] creating groups'
        create_permission_groups()

        print '[INFO] import sub constituencies'
        self.import_sub_constituencies_and_ballots()

        print '[INFO] import centers'
        self.import_centers()

        print '[INFO] import stations'
        self.import_stations()

        print '[INFO] import candidates'
        self.import_candidates()

        print '[INFO] import result forms'
        self.import_result_forms()

    def import_sub_constituencies_and_ballots(self):
        with open(SUB_CONSTITUENCIES_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                if invalid_line(row):
                    next

                row = empty_strings_to_none(row)

                try:
                    code_value = int(row[0])
                    ballot_number_general = row[3]
                    ballot_number_women = row[4]
                    number_of_ballots = row[5] and int(row[5])

                    ballot_general = None
                    ballot_women = None

                    if ballot_number_general:
                        ballot_general, created = Ballot.objects.get_or_create(
                            number=ballot_number_general,
                            race_type=RaceType.GENERAL)

                    if ballot_number_women:
                        ballot_women, created = Ballot.objects.get_or_create(
                            number=ballot_number_women,
                            race_type=RaceType.WOMEN)

                    if number_of_ballots == 2 and not (
                            ballot_general and ballot_women):
                        raise Exception(
                            'Missing ballot data: expected 2 ballots, missing '
                            + ('general' if ballot_number_women else 'women'))

                    _, created = SubConstituency.objects.get_or_create(
                        code=code_value,
                        field_office=row[1],
                        races=row[2],
                        ballot_general=ballot_general,
                        ballot_women=ballot_women,
                        number_of_ballots=number_of_ballots,
                        component_ballot=row[6] or False)

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
        id_to_ballot_order = {}

        with open(BALLOT_ORDER_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                id_to_ballot_order[row[0]] = row[1]

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

                candidate_id = row[0]
                sub_constituency = SubConstituency.objects.get(
                    code=row[7])

                if race_type != RaceType.WOMEN:
                    ballot = sub_constituency.ballot_general
                else:
                    ballot = sub_constituency.ballot_women

                _, created = Candidate.objects.get_or_create(
                    ballot=ballot,
                    candidate_id=candidate_id,
                    full_name=row[14],
                    order=id_to_ballot_order[candidate_id],
                    race_type=race_type)

    def import_result_forms(self):
        with open(RESULT_FORMS_PATH, 'rU') as f:
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

                _, created = ResultForm.objects.get_or_create(
                    barcode=row[7],
                    ballot=ballot,
                    center=center,
                    form_state=FormState.UNSUBMITTED,
                    gender=gender,
                    name=row[4],
                    office=row[5],
                    serial_number=row[8],
                    station_number=row[2])
