#!/usr/bin/env python

from functools import reduce
import csv
import re
import duckdb

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy
from django.conf import settings

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.permissions.groups import create_permission_groups
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager
from tally_ho.libs.utils.numbers import parse_int


BALLOT_ORDER_PATH = 'data/ballot_order.csv'
CANDIDATES_PATH = 'data/candidates.csv'
CENTERS_PATH = 'data/centers.csv'
RESULT_FORMS_PATH = 'data/result_forms.csv'
STATIONS_PATH = 'data/stations.csv'
SUB_CONSTITUENCIES_PATH = 'data/sub_constituencies.csv'

SPECIAL_VOTING = 'Special Voting'


def empty_string_to(value, default):
    return value if value and len(value) else default


def empty_strings_to_none(row):
    """Convert all empty strings in row to 0."""
    return [empty_string_to(f, None) for f in row]


def get_component_race_type(ballot_number_component, tally=None):
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
        4: RaceType.COMPONENT_TEBU,
        5: RaceType.PRESIDENTIAL
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


def process_sub_constituency_row(tally, row, command=None, logger=None):
    if invalid_line(row):
        next

    row = empty_strings_to_none(row)

    try:
        code_value, field_office, races, ballot_number_presidential,\
            ballot_number_general, ballot_number_women,\
            number_of_ballots, ballot_number_component = row[:8]

        code_value = int(code_value)
        number_of_ballots = number_of_ballots and int(
            number_of_ballots)

        ballot_component = None
        ballot_general = None
        ballot_women = None
        max_ballot_number = 3

        if ballot_number_component:
            component_race_type = get_component_race_type(
                ballot_number_component,
                tally=tally)

            ballot_component, _ = Ballot.objects.get_or_create(
                number=int(ballot_number_component),
                race_type=component_race_type,
                tally=tally)

        if ballot_number_presidential:
            ballot_presidential, _ = Ballot.objects.get_or_create(
                number=int(ballot_number_presidential),
                race_type=RaceType.PRESIDENTIAL,
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

        if number_of_ballots == max_ballot_number and not (
                ballot_general
                and ballot_women
                and ballot_presidential):
            missing_ballot = None
            if not ballot_general:
                missing_ballot = 'general'
            elif not ballot_women:
                missing_ballot = 'women'
            else:
                missing_ballot = 'presidential'

            raise Exception(
                'Missing ballot data: expected {} ballots, missing {}'
                .format(max_ballot_number, missing_ballot))

        SubConstituency.objects.get_or_create(
            code=code_value,
            field_office=field_office,
            races=races,
            ballot_component=ballot_component,
            ballot_presidential=ballot_presidential,
            ballot_general=ballot_general,
            ballot_women=ballot_women,
            number_of_ballots=number_of_ballots,
            tally=tally)

    except ValueError:
        msg = 'ValueError when parsing row: %s' % row
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def create_electrol_races_from_ballot_file_data(
        duckdb_ballots_data=None,
        tally=None,
        command=None,
        logger=None,
):
    """Create electrol races from ballot file data inside duckdb.

    :param duckdb_ballots_data: Ballot file data in duckdb format.
    :param tally: Electrol races tally.
    :param command: stdout command.
    :param logger: logger.
    :returns: Electrol races queryset."""
    try:
        electrol_races_columns =\
            getattr(settings, 'ELECTROL_RACES_COLUMNS_IN_BALLOT_FILE')
        electrol_races_data =\
            duckdb_ballots_data.project(
            ','.join(electrol_races_columns)).distinct().fetchall()
        bulk_mgr = BulkCreateManager(objs_count=len(electrol_races_data))

        for electrol_race in electrol_races_data:
            election_level, ballot_name = electrol_race
            bulk_mgr.add(ElectrolRace(
                            election_level=election_level,
                            ballot_name=ballot_name,
                            tally=tally))
        bulk_mgr.done()

        return ElectrolRace.objects.filter(tally=tally)
    except Exception as e:
        msg = 'Failed to create electrol races, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def create_ballots_from_ballot_file_data(
        duckdb_ballots_data=None,
        electrol_races=None,
        tally=None,
        command=None,
        logger=None,
):
    """Create ballots from ballot file data inside duckdb.

    :param duckdb_ballots_data: Ballot file data in duckdb format.
    :param electrol_races: Tally electrol races queryset.
    :param tally: tally queryset.
    :param command: stdout command.
    :param logger: logger.
    :returns: Ballots queryset."""
    try:
        bulk_mgr = BulkCreateManager(
            objs_count=len(duckdb_ballots_data.distinct().fetchall()))

        for electrol_race in electrol_races:
            str_query =\
                f"election_level = '{electrol_race.election_level}' AND" +\
                f" ballot_name = '{electrol_race.ballot_name}'"
            ballot_numbers =\
                duckdb_ballots_data.filter(
                    str_query).project('number').fetchall()
            for ballot_number_tuple in ballot_numbers:
                # TODO: Some ballot numbers in string format we need to
                # fiqure out how they should be handled here.
                ballot_number = parse_int(ballot_number_tuple[0])
                if ballot_number:
                    bulk_mgr.add(Ballot(
                                    number=ballot_number,
                                    electrol_race=electrol_race,
                                    tally=tally))
        bulk_mgr.done()

        return Ballot.objects.filter(tally=tally)
    except Exception as e:
        msg = 'Failed to create ballots, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def import_electrol_races_and_ballots(
        tally=None,
        ballots_file_path=None,
        command=None,
        logger=None):
    """Create electrol races and ballots from a ballots csv file.

    :param tally: tally queryset.
    :param ballots_file_path: ballots csv file path.
    :param command: stdout command.
    :param logger: logger.
    :returns: Ballots count."""
    try:
        file_path = ballots_file_path or SUB_CONSTITUENCIES_PATH
        ballots_data = duckdb.from_csv_auto(file_path, header=True)
        electrol_races = create_electrol_races_from_ballot_file_data(
            duckdb_ballots_data=ballots_data,
            tally=tally,
            command=command,
            logger=logger,
        )
        ballots = create_ballots_from_ballot_file_data(
            duckdb_ballots_data=ballots_data,
            electrol_races=electrol_races,
            tally=tally,
            command=command,
            logger=logger,
        )

        return ballots.count()
    except Exception as e:
        msg = 'Error occured while trying to create ballots: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def create_ballots_from_sub_con_data(
        duckdb_sub_con_data=None,
        sub_con_data_count=None,
        electrol_races=None,
        tally=None,
        command=None,
        logger=None,
):
    try:
        bulk_mgr = BulkCreateManager(objs_count=sub_con_data_count)
        electrol_races_by_ballot_name =\
            {
                electrol_race.ballot_name:\
                electrol_race for electrol_race in electrol_races
            }
        ballot_names =\
            list(set([electrol_race.ballot_name
                        for electrol_race in electrol_races]))
        for ballot_name in ballot_names:
            distinct_ballot_numbers =\
                duckdb_sub_con_data.project(
                str(ballot_name)).filter(
                '{column} IS NOT NULL'.format(
                column=str(ballot_name))).distinct().fetchall()
            if len(distinct_ballot_numbers):
                for ballot_number_tuple in distinct_ballot_numbers:
                    ballot_number = parse_int(ballot_number_tuple[0])
                    if ballot_number:
                        electrol_race = None
                        if ballot_name == 'ballot_number_component':
                            electrol_race =\
                                    electrol_races.filter(
                                    component_ballot_numbers__contains=[
                                        ballot_number])
                        else:
                            electrol_race =\
                                electrol_races_by_ballot_name.get(
                                        ballot_name)
                        bulk_mgr.add(Ballot(
                                    number=ballot_number,
                                    electrol_race=electrol_race,
                                    tally=tally))
        bulk_mgr.done()

        return Ballot.objects.filter(tally=tally)
    except Exception as e:
        msg = 'Failed to create ballots, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def create_sub_constituencies_with_ballots(
        duckdb_sub_con_data=None,
        sub_con_data_count=None,
        electrol_races=None,
        ballots=None,
        tally=None,
        command=None,
        logger=None
):
    try:
        sub_constituency_model_unique_field = 'code'
        sub_constituency_code_column_name_in_duckdb_data =\
            'sub_constituency_code'
        bulk_mgr = BulkCreateManager(objs_count=sub_con_data_count)
        electrol_races_by_ballot_name =\
            {
                electrol_race.ballot_name:\
                electrol_race for electrol_race in electrol_races
            }
        ballots_by_ballot_number =\
            {
                ballot.number:\
                ballot for ballot in ballots
            }
        sub_con_columns =\
            getattr(settings, 'SUB_CONSTITUENCY_COLUMN_NAMES')
        sub_constituency_data =\
                    duckdb_sub_con_data.project(
            ','.join(sub_con_columns)).fetchall()

        for row in sub_constituency_data:
            kwargs = {}
            many_to_many_fields = {
                'ballots': []
            }

            for i, value in enumerate(row):
                # Check if row value is a ballot
                row_value_column_name = sub_con_columns[i]
                if row_value_column_name ==\
                        sub_constituency_code_column_name_in_duckdb_data:
                        if parse_int(value):
                            kwargs[sub_constituency_model_unique_field] =\
                                parse_int(value)
                        else:
                            break
                elif electrol_races_by_ballot_name.get(
                    row_value_column_name):
                    ballot_number = parse_int(value)
                    ballot = ballots_by_ballot_number.get(ballot_number)\
                        if ballot_number else None
                    if ballot:
                        many_to_many_fields['ballots'].append(ballot)
                else:
                    kwargs[row_value_column_name] = value

            if len(kwargs.items()):
                kwargs['tally'] = tally
                bulk_mgr.add(
                    SubConstituency(**kwargs),
                    model_unique_field=sub_constituency_model_unique_field,
                    many_to_many_fields=many_to_many_fields)
        bulk_mgr.done(
            model_class=SubConstituency,
            model_unique_field=sub_constituency_model_unique_field
        )
    except Exception as e:
        msg = 'Failed to create sub constituencies, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)


def import_sub_constituencies_and_ballots(
        tally=None,
        sub_con_file_path=None,
        command=None,
        logger=None):
    try:
        electrol_races = ElectrolRace.objects.all()
        file_path = sub_con_file_path or SUB_CONSTITUENCIES_PATH
        sub_con_data = duckdb.from_csv_auto(file_path)
        records_count = len(sub_con_data.fetchall())
        ballots = create_ballots_from_sub_con_data(
            duckdb_sub_con_data=sub_con_data,
            sub_con_data_count=records_count,
            electrol_races=electrol_races,
            tally=tally,
            command=command,
            logger=logger,
        )
        create_sub_constituencies_with_ballots(
            duckdb_sub_con_data=sub_con_data,
            sub_con_data_count=records_count,
            electrol_races=electrol_races,
            ballots=ballots,
            tally=tally,
            command=command,
            logger=logger,
        )
        elements_processed =\
            SubConstituency.objects.filter(tally=tally).count()
        return records_count if elements_processed else None
    except Exception as e:
        msg = 'Error occured: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)



def process_center_row(tally, row, command=None, logger=None):
    if not invalid_line(row):
        try:
            constituency_name = row[5]
        except ValueError:
            constituency_name = None

        constituency, _ = Constituency.objects.get_or_create(
            name=constituency_name.strip(),
            tally=tally)

        sc_code = row[6]
        sub_constituency = None

        if sc_code == SPECIAL_VOTING:
            center_type = CenterType.SPECIAL
        else:
            sc_code = int(row[6])
            sub_constituency = SubConstituency.objects.get(
                code=sc_code,
                tally=tally)
            sub_constituency.constituency = constituency
            sub_constituency.save(update_fields=['constituency'])
            center_type = CenterType.GENERAL

        try:
            region_name = row[1]
        except ValueError:
            region_name = None

        region, _ = Region.objects.get_or_create(
            name=region_name.strip(),
            tally=tally)

        try:
            office_number = int(row[3])
        except ValueError:
            office_number = None

        office, _ = Office.objects.get_or_create(
            number=office_number,
            name=row[4].strip(),
            tally=tally,
            region=region)

        Center.objects.get_or_create(
            region=region_name,
            code=row[2],
            office=office,
            sub_constituency=sub_constituency,
            name=row[8],
            mahalla=row[9],
            village=row[10],
            center_type=center_type,
            longitude=strip_non_numeric(row[12]),
            latitude=strip_non_numeric(row[13]),
            tally=tally,
            constituency=constituency)


def import_centers(tally=None, centers_file=None):
    file_to_parse = centers_file if centers_file else open(CENTERS_PATH, 'r')

    with file_to_parse as f:
        reader = csv.reader(f)
        next(reader)  # ignore header

        for row in reader:
            process_center_row(tally, row)


def process_station_row(tally, row, command=None, logger=None):
    center_code, center_name, sc_code, station_number, gender,\
        registrants = row[0:6]

    try:
        center = Center.objects.get(code=center_code, tally=tally)
    except Center.DoesNotExist:
        center, created = Center.objects.get_or_create(
            code=center_code,
            name=center_name,
            tally=tally)

    try:
        # attempt to convert SC to a number
        sc_code = int(float(sc_code))
        sub_constituency = SubConstituency.objects.get(
            code=sc_code, tally=tally)
    except (SubConstituency.DoesNotExist, ValueError):
        # FIXME What to do if SubConstituency does not exist
        sub_constituency = None
        msg = 'SubConstituency "%s" does not exist' % sc_code
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        # Todo: Uncomment after cleaning initial tally files
        # raise SubConstituency.DoesNotExist(msg)

    gender = getattr(Gender, gender.upper())

    _, created = Station.objects.get_or_create(
        tally=tally,
        center=center,
        sub_constituency=sub_constituency,
        gender=gender,
        registrants=empty_string_to(registrants, None),
        station_number=station_number)


def import_stations(command, tally=None, stations_file=None):
    file_to_parse = stations_file if stations_file else open(
        STATIONS_PATH, 'r')

    with file_to_parse as f:
        reader = csv.reader(f)
        next(reader)  # ignore header

        for row in reader:
            process_station_row(tally, row, command=command)


def process_candidate_row(
        tally,
        row,
        id_to_ballot_order,
        command=None,
        logger=None
):
    candidate_id = row[0]
    ballot_number = row[7]
    full_name = row[14]

    try:
        ballot = Ballot.objects.get(
            number=ballot_number, tally=tally)
        Candidate.objects.get_or_create(
            ballot=ballot,
            candidate_id=candidate_id,
            full_name=full_name,
            order=id_to_ballot_order[candidate_id],
            tally=tally)

    except Ballot.DoesNotExist as e:
        msg = f'Ballot {ballot_number} does not exist, error: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        pass


def import_candidates(tally=None,
                      candidates_file=None,
                      ballot_file=None):
    candidates_file_to_parse = candidates_file if candidates_file else open(
        CANDIDATES_PATH, 'r')
    ballot_file_to_parse = ballot_file if ballot_file else open(
        BALLOT_ORDER_PATH, 'r')

    id_to_ballot_order = {}

    with ballot_file_to_parse as f:
        reader = csv.reader(f)
        next(reader)  # ignore header

        for row in reader:
            id_, ballot_number = row
            id_to_ballot_order[id_] = ballot_number

    with candidates_file_to_parse as f:
        reader = csv.reader(f)
        next(reader)  # ignore header

        for row in reader:
            process_candidate_row(tally, row, id_to_ballot_order)


def process_results_form_row(tally, row, command=None, logger=None):
    replacement_count = 0

    row = empty_strings_to_none(row)
    # take first 11 values
    ballot_number, code, station_number, gender, name,\
        office_name, _, barcode, serial_number, _, region_id = row[0:11]

    gender = gender and getattr(Gender, gender.upper())
    ballot = None

    if ballot_number:
        try:
            ballot = Ballot.objects.get(number=ballot_number, tally=tally)
            if not ballot.active:
                msg = 'Race for ballot "%s" is disabled' % ballot_number
                if command:
                    command.stdout.write(command.style.WARNING(msg))
                if logger:
                    logger.warning(msg)

        except Ballot.DoesNotExist:
            msg = str('Ballot "%s" does not exist for tally "%s"') %\
                (ballot_number, tally.name)
            if command:
                command.stdout.write(command.style.WARNING(msg))
            if logger:
                logger.warning(msg)
            # Todo: Uncomment after cleaning initial tally files
            # raise Ballot.DoesNotExist(msg)

    center = None

    if code:
        try:
            center = Center.objects.get(code=code, tally=tally)
            if not center.active:
                msg = 'Selected center "%s" is disabled' % code
                if command:
                    command.stdout.write(command.style.WARNING(msg))
                if logger:
                    logger.warning(msg)

        except Center.DoesNotExist:
            msg = 'Center "%s" does not exist' % code
            if command:
                command.stdout.write(command.style.WARNING(msg))
            if logger:
                logger.warning(msg)
            # Todo: Uncomment after cleaning initial tally files
            # raise Center.DoesNotExist(msg)

    if station_number and center:
        try:
            station = Station.objects.get(
                station_number=station_number,
                center=center)
            if not station.active:
                msg = 'Selected station "%s" is disabled' % station_number
                if command:
                    command.stdout.write(command.style.WARNING(msg))
                if logger:
                    logger.warning(msg)

        except Station.DoesNotExist:
            msg = str('Station "%s" does not exist for center "%s"') %\
                (station_number, code)
            if command:
                command.stdout.write(command.style.WARNING(msg))
            if logger:
                logger.warning(msg)
            # Todo: Uncomment after cleaning initial tally files
            # raise Station.DoesNotExist(msg)

    if center and center.sub_constituency and \
            ballot.number != center.sub_constituency.code:
        msg = str('Ballot number "%s" do not match for center "%s" '
                  'and station "%s"') %\
            (ballot.number, code, station_number)
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

    office = None

    if office_name:
        try:
            office = Office.objects.get(
                name=office_name.strip(),
                tally=tally,
                region__id=region_id)
        except Office.DoesNotExist:
            msg = 'Office "%s" does not exist' % office_name
            if command:
                command.stdout.write(command.style.WARNING(msg))
            if logger:
                logger.warning(msg)
            # Todo: Uncomment after cleaning initial tally files
            # raise Office.DoesNotExist(msg)

    is_replacement = center is None

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
    except ResultForm.DoesNotExist:
        ResultForm.objects.create(**kwargs)
    else:
        if is_replacement:
            form.is_replacement = is_replacement
            form.save()

    return replacement_count


def import_result_forms(command, tally=None, result_forms_file=None):
    file_to_parse = result_forms_file if result_forms_file else open(
        RESULT_FORMS_PATH, 'r')
    replacement_count = 0

    with file_to_parse as f:
        reader = csv.reader(f)
        next(reader)  # ignore header

        for row in reader:
            replacement_count += process_results_form_row(
                tally, row, command=command)

    command.stdout.write(command.style.NOTICE(
        'Number of replacement forms: %s' % replacement_count))


class Command(BaseCommand):
    help = gettext_lazy("Import polling data.")

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('creating groups'))
        create_permission_groups()

        self.stdout.write(self.style.NOTICE('import sub constituencies'))
        import_sub_constituencies_and_ballots()

        self.stdout.write(self.style.NOTICE('import centers'))
        import_centers()

        self.stdout.write(self.style.NOTICE('import stations'))
        import_stations(self)

        self.stdout.write(self.style.NOTICE('import candidates'))
        import_candidates()

        self.stdout.write(self.style.NOTICE('import result forms'))
        import_result_forms(self)
