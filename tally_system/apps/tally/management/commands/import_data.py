#!/usr/bin/env python

import csv
import re

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from tally_system.apps.tally.models.ballot import Ballot
from tally_system.apps.tally.models.candidate import Candidate
from tally_system.apps.tally.models.center import Center
from tally_system.apps.tally.models.office import Office
from tally_system.apps.tally.models.result_form import ResultForm
from tally_system.apps.tally.models.station import Station
from tally_system.apps.tally.models.sub_constituency import SubConstituency
from tally_system.libs.models.enums.center_type import CenterType
from tally_system.libs.models.enums.form_state import FormState
from tally_system.libs.models.enums.gender import Gender
from tally_system.libs.models.enums.race_type import RaceType
from tally_system.libs.permissions.groups import create_permission_groups

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


def get_component_race_type(ballot_number_component):
    return {
        '54': RaceType.COMPONENT_AMAZIGH,
        '55': RaceType.COMPONENT_TWARAG,
        '56': RaceType.COMPONENT_TEBU,
        '57': RaceType.COMPONENT_TWARAG,
        '58': RaceType.COMPONENT_TEBU,
    }[ballot_number_component]


def get_race_type(race_code):
    return {
        0: RaceType.GENERAL,
        1: RaceType.WOMEN,
        2: RaceType.COMPONENT_AMAZIGH,
        3: RaceType.COMPONENT_TWARAG,
        4: RaceType.COMPONENT_TEBU
    }[int(race_code)]


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
        self.import_result_forms(RESULT_FORMS_PATH)

    def import_sub_constituencies_and_ballots(self):
        with open(SUB_CONSTITUENCIES_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                if invalid_line(row):
                    next

                row = empty_strings_to_none(row)

                try:
                    code_value, field_office, races, ballot_number_general,\
                        ballot_number_women, number_of_ballots,\
                        ballot_number_component = row[:7]

                    code_value = int(code_value)
                    number_of_ballots = number_of_ballots and int(
                        number_of_ballots)

                    ballot_component = None
                    ballot_general = None
                    ballot_women = None

                    if ballot_number_component:
                        component_race_type = get_component_race_type(
                            ballot_number_component)

                        ballot_component, _ = Ballot.objects.get_or_create(
                            number=ballot_number_component,
                            race_type=component_race_type)

                    if ballot_number_general:
                        ballot_general, _ = Ballot.objects.get_or_create(
                            number=ballot_number_general,
                            race_type=RaceType.GENERAL)

                    if ballot_number_women:
                        ballot_women, _ = Ballot.objects.get_or_create(
                            number=ballot_number_women,
                            race_type=RaceType.WOMEN)

                    if number_of_ballots == 2 and not (
                            ballot_general and ballot_women):
                        raise Exception(
                            'Missing ballot data: expected 2 ballots, missing '
                            + ('general' if ballot_number_women else 'women'))

                    _, created = SubConstituency.objects.get_or_create(
                        code=code_value,
                        field_office=field_office,
                        races=races,
                        ballot_component=ballot_component,
                        ballot_general=ballot_general,
                        ballot_women=ballot_women,
                        number_of_ballots=number_of_ballots)

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

                    try:
                        office_number = int(row[3])
                    except ValueError:
                        office_number = None

                    office, _ = Office.objects.get_or_create(
                        number=office_number,
                        name=row[4].strip())

                    Center.objects.get_or_create(
                        region=row[1],
                        code=row[2],
                        office=office,
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
                center_code, center_name, sc_code, station_number, gender,\
                    registrants = row[0:6]

                try:
                    center = Center.objects.get(code=center_code)
                except Center.DoesNotExist:
                    center, created = Center.objects.get_or_create(
                        code=center_code,
                        name=center_name)

                try:
                    # attempt to convert SC to a number
                    sc_code = int(float(sc_code))
                    sub_constituency = SubConstituency.objects.get(
                        code=sc_code)
                except (SubConstituency.DoesNotExist, ValueError):
                    print('[WARNING] SubConstituency "%s" does not exist' %
                          sc_code)

                gender = getattr(Gender, gender.upper())

                _, created = Station.objects.get_or_create(
                    center=center,
                    sub_constituency=sub_constituency,
                    gender=gender,
                    registrants=empty_string_to(registrants, None),
                    station_number=station_number)

    def import_candidates(self):
        id_to_ballot_order = {}

        with open(BALLOT_ORDER_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                id_, ballot_number = row
                id_to_ballot_order[id_] = ballot_number

        with open(CANDIDATES_PATH, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                candidate_id = row[0]
                code = row[7]
                full_name = row[14]
                race_code = row[18]

                race_type = get_race_type(race_code)

                try:
                    sub_constituency = SubConstituency.objects.get(
                        code=code)

                    if race_type != RaceType.WOMEN:
                        ballot = sub_constituency.ballot_general
                    else:
                        ballot = sub_constituency.ballot_women

                except SubConstituency.DoesNotExist:
                    ballot = Ballot.objects.get(number=code)
                    sub_constituency = ballot.sc_component

                _, created = Candidate.objects.get_or_create(
                    ballot=ballot,
                    candidate_id=candidate_id,
                    full_name=full_name,
                    order=id_to_ballot_order[candidate_id],
                    race_type=race_type)

    def import_result_forms(self, path):
        replacement_count = 0

        with open(path, 'rU') as f:
            reader = csv.reader(f)
            reader.next()  # ignore header

            for row in reader:
                row = empty_strings_to_none(row)
                ballot_number, code, station_number, gender, name,\
                    office_name, _, barcode, serial_number = row

                ballot = Ballot.objects.get(number=ballot_number)
                gender = gender and getattr(Gender, gender.upper())
                center = None

                try:
                    center = Center.objects.get(code=code)
                except Center.DoesNotExist:
                    pass

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
                    'name': name,
                    'office': office,
                    'serial_number': serial_number,
                    'station_number': station_number,
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
