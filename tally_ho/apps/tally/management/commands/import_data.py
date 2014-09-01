#!/usr/bin/env python

import csv
import re

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.permissions.groups import create_permission_groups

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


def process_sub_constituency_row(tally, row):
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
                ballot_number_component,
                tally=tally)

            ballot_component, _ = Ballot.objects.get_or_create(
                number=int(ballot_number_component),
                race_type=component_race_type,
                tally=tally)

        if ballot_number_general:
            ballot_general, _ = Ballot.objects.get_or_create(
                number=int(ballot_number_general),
                race_type=RaceType.GENERAL,
                tally=tally)

        if ballot_number_women:
            ballot_women, _ = Ballot.objects.get_or_create(
                number=int(ballot_number_women),
                race_type=RaceType.WOMEN,
                tally=tally)

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
            number_of_ballots=number_of_ballots,
            tally=tally)

    except ValueError:
        pass


def import_sub_constituencies_and_ballots(tally = None, subconst_file = None):
    file_to_parse = subconst_file if subconst_file else open(SUB_CONSTITUENCIES_PATH, 'rU')
    elements_processed = 0;

    with file_to_parse as f:
        reader = csv.reader(f)
        reader.next()  # ignore header

        for row in reader:
            process_sub_constituency_row(tally, row)
            elements_processed += 1

    return elements_processed


def process_center_row(tally, row):
    if not invalid_line(row):
        sc_code = row[6]
        sub_constituency = None

        if sc_code == SPECIAL_VOTING:
            center_type = CenterType.SPECIAL
        else:
            sc_code = int(row[6])
            sub_constituency = SubConstituency.objects.get(
                code=sc_code,
                tally=tally)
            center_type = CenterType.GENERAL

        try:
            office_number = int(row[3])
        except ValueError:
            office_number = None

        office, _ = Office.objects.get_or_create(
            number=office_number,
            name=row[4].strip(),
            tally=tally)

        Center.objects.get_or_create(
            region=row[1],
            code=row[2],
            office=office,
            sub_constituency=sub_constituency,
            name=unicode(row[8], 'utf-8'),
            mahalla=row[9],
            village=row[10],
            center_type=center_type,
            longitude=strip_non_numeric(row[12]),
            latitude=strip_non_numeric(row[13]),
            tally=tally)


def import_centers(tally = None, centers_file = None):
    file_to_parse = centers_file if centers_file else open(CENTERS_PATH, 'rU')

    with file_to_parse as f:
        reader = csv.reader(f)
        reader.next()  # ignore header

        for row in reader:
            process_center_row(tally, row)


def process_station_row(tally, row):
    center_code, center_name, sc_code, station_number, gender,\
        registrants = row[0:6]

    try:
        center = Center.objects.get(code=center_code, tally=tally)
    except Center.DoesNotExist:
        center, created = Center.objects.get_or_create(
            code=center_code,
            name=unicode(center_name, 'utf-8'),
            tally=tally)

    try:
        # attempt to convert SC to a number
        sc_code = int(float(sc_code))
        sub_constituency = SubConstituency.objects.get(
            code=sc_code, tally=tally)
    except (SubConstituency.DoesNotExist, ValueError):
        #FIXME: What to do if SubConstituency does not exist
        sub_constituency = None
        print('[WARNING] SubConstituency "%s" does not exist' %
              sc_code)

    gender = getattr(Gender, gender.upper())

    _, created = Station.objects.get_or_create(
        center=center,
        sub_constituency=sub_constituency,
        gender=gender,
        registrants=empty_string_to(registrants, None),
        station_number=station_number)


def import_stations(tally = None, stations_file = None):
    file_to_parse = stations_file if stations_file else open(STATIONS_PATH, 'rU')

    with file_to_parse as f:
        reader = csv.reader(f)
        reader.next()  # ignore header

        for row in reader:
            process_station_row(tally, row)


def process_candidate_row(tally, row, id_to_ballot_order):
    candidate_id = row[0]
    code = row[7]
    full_name = row[14]
    race_code = row[18]

    race_type = get_race_type(race_code)

    try:
        sub_constituency = SubConstituency.objects.get(
            code=code, tally=tally)

        if race_type != RaceType.WOMEN:
            ballot = sub_constituency.ballot_general
        else:
            ballot = sub_constituency.ballot_women

    except SubConstituency.DoesNotExist:
        ballot = Ballot.objects.get(number=code, tally=tally)
        sub_constituency = ballot.sc_component

    _, created = Candidate.objects.get_or_create(
        ballot=ballot,
        candidate_id=candidate_id,
        full_name=unicode(full_name, 'utf-8'),
        order=id_to_ballot_order[candidate_id],
        race_type=race_type,
        tally=tally)


def import_candidates(tally = None, candidates_file = None, ballot_file = None):
    candidates_file_to_parse = candidates_file  if candidates_file else open(CANDIDATES_PATH, 'rU')
    ballot_file_to_parse = ballot_file if ballot_file else open(BALLOT_ORDER_PATH, 'rU')

    id_to_ballot_order = {}

    with ballot_file_to_parse as f:
        reader = csv.reader(f)
        reader.next()  # ignore header

        for row in reader:
            id_, ballot_number = row
            id_to_ballot_order[id_] = ballot_number

    with candidates_file_to_parse as f:
        reader = csv.reader(f)
        reader.next()  # ignore header

        for row in reader:
            process_candidate_row(tally, row, id_to_ballot_order)


def process_results_form_row(tally, row):
    replacement_count = 0

    row = empty_strings_to_none(row)
    ballot_number, code, station_number, gender, name,\
        office_name, _, barcode, serial_number = row

    ballot = Ballot.objects.get(number=ballot_number, tally=tally)
    gender = gender and getattr(Gender, gender.upper())
    center = None

    try:
        center = Center.objects.get(code=code, tally=tally)
    except Center.DoesNotExist:
        pass

    office = None

    if office_name:
        try:
            office = Office.objects.get(name=office_name.strip(), tally=tally)
        except Office.DoesNotExist:
            print('[WARNING] Office "%s" does not exist' %
                  office_name)

    is_replacement = True if center is None else False

    if is_replacement:
        replacement_count = 1

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
        'is_replacement': is_replacement,
        'tally': tally
    }

    try:
        form = ResultForm.objects.get(barcode=barcode, tally=tally)
        #print '[INFO] Found with barcode: %s' % barcode
    except ResultForm.DoesNotExist:
        #print '[INFO] Create with barcode: %s' % barcode
        ResultForm.objects.create(**kwargs)
    else:
        if is_replacement:
            form.is_replacement = is_replacement
            form.save()

    return replacement_count


def import_result_forms(tally = None, result_forms_file = None):
    file_to_parse = result_forms_file  if result_forms_file else open(RESULT_FORMS_PATH, 'rU')
    replacement_count = 0

    with file_to_parse as f:
        reader = csv.reader(f)
        reader.next()  # ignore header

        for row in reader:
            replacement_count += process_results_form_row(tally, row)

    print '[INFO] Number of replacement forms: %s' % replacement_count


class Command(BaseCommand):
    help = ugettext_lazy("Import polling data.")

    def handle(self, *args, **kwargs):
        print '[INFO] creating groups'
        create_permission_groups()

        print '[INFO] import sub constituencies'
        import_sub_constituencies_and_ballots()

        print '[INFO] import centers'
        import_centers()

        print '[INFO] import stations'
        import_stations()

        print '[INFO] import candidates'
        import_candidates()

        print '[INFO] import result forms'
        import_result_forms()

