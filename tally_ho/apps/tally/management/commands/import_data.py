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
from tally_ho.libs.utils.query_set_helpers import (
    BulkCreateManager,
    BulkUpdateManyToManyManager
)
from tally_ho.libs.utils.numbers import parse_int


BALLOT_ORDER_PATH = 'data/ballot_order.csv'
CANDIDATES_PATH = 'data/candidates.csv'
CENTERS_PATH = 'data/centers.csv'
RESULT_FORMS_PATH = 'data/result_forms.csv'
STATIONS_PATH = 'data/stations.csv'
BALLOTS_PATH = 'data/ballots.csv'
SUB_CONSTITUENCIES_PATH = 'data/sub_constituencies.csv'
SUB_CONSTITUENCIES_BALLOTS_PATH = 'data/sub_constituency_ballots.csv'

OCV_VOTING = 'OCV Voting'
SPECIAL_VOTING = 'Special Voting'
NO_CONSTITUENCY = 'No Constituency'
NO_CONSTITUENCY_SUB_CON_NUMBER = 999

NO_CENTER_NAME_AVAILABLE = '#N/A'


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
    :returns: None"""
    try:
        electrol_race_cols_to_model_fields_mapping =\
            getattr(settings,
                    'ELECTROL_RACE_COLS_TO_MODEL_FIELDS_MAPPING')
        electrol_races_columns =\
            [list(item.keys())[0] for item in\
                electrol_race_cols_to_model_fields_mapping]
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

        return
    except Exception as e:
        msg = 'Failed to create electrol races, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def generate_duckdb_electrol_race_str_query(electrol_race=None):
    """Generate string query for querying electrol race columns
    in ballots file using duckdb.

    :param electrol_race: electrol race queryset.
    :returns: string query."""
    electrol_race_cols_to_model_fields_mapping =\
            getattr(settings,
                    'ELECTROL_RACE_COLS_TO_MODEL_FIELDS_MAPPING')
    str_query = None
    for electrol_race_mapping in\
            electrol_race_cols_to_model_fields_mapping:
            electrol_race_column_name =\
                list(electrol_race_mapping.keys())[0]
            electrol_race_field_name = electrol_race_mapping.get(
                electrol_race_column_name
            )
            electrol_race_field_val =\
                getattr(electrol_race, electrol_race_field_name)

            if str_query is None:
                str_query =\
                    f" {electrol_race_column_name}" +\
                    f" = '{electrol_race_field_val}'"
            else:
                str_query +=\
                    f" AND {electrol_race_column_name}" +\
                    f" = '{electrol_race_field_val}'"

    return str_query

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
    :returns: None."""
    try:
        bulk_mgr = BulkCreateManager(
            objs_count=len(duckdb_ballots_data.distinct().fetchall()))
        ballot_name_column_name =\
            getattr(settings,
                    'BALLOT_NAME_COLUMN_NAME_IN_BALLOT_FILE')

        for electrol_race in electrol_races:
            str_query =\
                generate_duckdb_electrol_race_str_query(
                    electrol_race=electrol_race)
            ballot_numbers =\
                duckdb_ballots_data.filter(
                    str_query).project(ballot_name_column_name).fetchall()
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

        return
    except Exception as e:
        msg = 'Failed to create ballots, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def import_electrol_races_and_ballots_from_ballots_file(
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
        file_path = ballots_file_path or BALLOTS_PATH
        ballots_data = duckdb.from_csv_auto(file_path, header=True)
        create_electrol_races_from_ballot_file_data(
            duckdb_ballots_data=ballots_data,
            tally=tally,
            command=command,
            logger=logger,
        )
        electrol_races = ElectrolRace.objects.filter(tally=tally)

        create_ballots_from_ballot_file_data(
            duckdb_ballots_data=ballots_data,
            electrol_races=electrol_races,
            tally=tally,
            command=command,
            logger=logger,
        )

        return len(ballots_data.fetchall())
    except Exception as e:
        msg = 'Error occured while trying to create ballots: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def create_constituencies_from_sub_con_file_data(
        duckdb_sub_con_data=None,
        tally=None,
        command=None,
        logger=None,
):
    """Create constituencies from sub constituencies file data inside duckdb.

    :param duckdb_sub_con_data: sub constituencies file data in duckdb format.
    :param tally: tally queryset.
    :param command: stdout command.
    :param logger: logger.
    :returns: None."""
    try:
        constituency_column_name =\
            getattr(settings,
                    'CONSTITUENCY_COLUMN_NAME_IN_SUB_CONSTITUENCY_FILE')
        constitiencies_names_list =\
            duckdb_sub_con_data.project(
            constituency_column_name).distinct().fetchall()
        bulk_mgr = BulkCreateManager(
            objs_count=len(constitiencies_names_list))

        for constitiency_name_tuple in constitiencies_names_list:
            constitiency_name = constitiency_name_tuple[0]
            if constitiency_name is not None:
                bulk_mgr.add(Constituency(
                                name=constitiency_name,
                                tally=tally))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = 'Failed to create constituencies, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def create_sub_constituencies_from_sub_con_file_data(
        duckdb_sub_con_data=None,
        constituencies_by_name=None,
        tally=None,
        command=None,
        logger=None,
):
    """Create sub constituencies from sub constituencies file data
        inside duckdb.

    :param duckdb_sub_con_data: sub constituencies file data in duckdb format.
    :param constituencies_by_name: tally constituencies_by_name queryset.
    :param tally: tally queryset.
    :param command: stdout command.
    :param logger: logger.
    :returns: None."""
    try:
        sub_con_cols_names_list =\
            getattr(settings,
                    'SUB_CONSTITUENCY_COLUMN_NAMES')
        sub_cons_data =\
                    duckdb_sub_con_data.project(
                    ','.join(sub_con_cols_names_list)).distinct().fetchall()
        bulk_mgr = BulkCreateManager(
            objs_count=len(sub_cons_data))

        for sub_con_vals_tuple in sub_cons_data:
            kwargs = {}
            code, number_of_ballots, constituency_name, sub_con_name =\
                list(sub_con_vals_tuple)
            parsed_sub_con_code = parse_int(code)
            if parsed_sub_con_code:
                kwargs['tally'] = tally
                kwargs['code'] = parsed_sub_con_code
                kwargs['name'] = sub_con_name
                kwargs['number_of_ballots'] = number_of_ballots
                kwargs['constituency'] =\
                    constituencies_by_name.get(constituency_name)

            if len(kwargs.items()):
                bulk_mgr.add(SubConstituency(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = 'Failed to create sub constituencies, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def import_sub_constituencies_and_constituencies_from_sub_cons_file(
        tally=None,
        sub_constituencies_file_path=None,
        command=None,
        logger=None):
    """Create sub constituencies and constituencies from a sub constituencies
    csv file.

    :param tally: tally queryset.
    :param sub_constituencies_file_path: sub constituencies csv file path.
    :param command: stdout command.
    :param logger: logger.
    :returns: Sub Constituencies count."""
    try:
        file_path = sub_constituencies_file_path or SUB_CONSTITUENCIES_PATH
        duckdb_sub_con_data = duckdb.from_csv_auto(file_path, header=True)
        create_constituencies_from_sub_con_file_data(
            duckdb_sub_con_data=duckdb_sub_con_data,
            tally=tally,
            command=command,
            logger=logger,
        )
        constituencies_by_name =\
                {
                    constituency.name:\
                    constituency for constituency in\
                        Constituency.objects.filter(tally=tally)
                }
        create_sub_constituencies_from_sub_con_file_data(
            duckdb_sub_con_data=duckdb_sub_con_data,
            constituencies_by_name=constituencies_by_name,
            tally=tally,
            command=command,
            logger=logger,
        )

        return len(duckdb_sub_con_data.fetchall())
    except Exception as e:
        msg =\
            'Error occured while trying to create sub cons and cons: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def set_sub_constituencies_ballots_from_sub_con_ballots_file_data(
        duckdb_sub_con_ballots_data=None,
        tally=None,
        command=None,
        logger=None,
):
    """Set sub constituencies ballots from sub constituencies ballots file data
        inside duckdb.

    :param duckdb_sub_con_ballots_data: sub cons ballots data in duckdb format.
    :param tally: tally queryset.
    :param command: stdout command.
    :param logger: logger.
    :returns: None."""
    try:
        sub_cons_instances_by_code =\
            {
                sub_con.code:\
                sub_con for sub_con in
                SubConstituency.objects.filter(tally=tally)
            }
        ballots_instances_by_number =\
            {
                ballot.number:\
                ballot for ballot in
                Ballot.objects.filter(tally=tally)
            }
        sub_con_code_col_name =\
            getattr(settings,
                    'SUB_CONSTITUENCY_COD_COL_NAME_IN_SUB_CON_BALLOTS_FILE')
        sub_con_code_data =\
                    duckdb_sub_con_ballots_data.project(
            f"{sub_con_code_col_name}").distinct().fetchall()
        ballot_number_col_name =\
            getattr(settings,
                    'BALLOT_NUMBER_COL_NAME_IN_SUB_CON_BALLOTS_FILE')
        bulk_mgr =\
            BulkUpdateManyToManyManager(instances_count=len(sub_con_code_data))

        for sub_con_code_tuple in sub_con_code_data:
            sub_con_code = parse_int(sub_con_code_tuple[0])
            if sub_con_code is None:
                continue
            sub_con_instance = sub_cons_instances_by_code.get(sub_con_code)
            if sub_con_instance is None:
                continue
            ballot_numbers =\
                duckdb_sub_con_ballots_data.filter(
                f"{sub_con_code_col_name} = '{sub_con_code}'").project(
                ballot_number_col_name).fetchall()
            many_to_many_fields = {
                'ballots': []
            }
            for ballot_number_tuple in ballot_numbers:
                ballot_number = parse_int(ballot_number_tuple[0])
                if ballot_number is None:
                    continue
                ballot_instance =\
                    ballots_instances_by_number.get(ballot_number)
                if ballot_instance is None:
                    continue
                many_to_many_fields['ballots'].append(ballot_instance)

            if sub_con_instance and len(many_to_many_fields.get('ballots')):
                bulk_mgr.add({
                    'instance': sub_con_instance,
                    'many_to_many_fields': many_to_many_fields,
                })

        bulk_mgr.done()

        return
    except Exception as e:
        msg = 'Failed to update sub constituencies, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)

def import_sub_constituencies_ballots_from_sub_cons_ballots_file(
        tally=None,
        sub_constituencies_ballots_file_path=None,
        command=None,
        logger=None):
    """Import sub constituencies ballots from a sub constituencies ballots
    csv file.

    :param tally: tally queryset.
    :param sub_constituencies_file_path: sub constituencies csv file path.
    :param command: stdout command.
    :param logger: logger.
    :returns: Sub Constituencies count."""
    try:
        file_path =\
            sub_constituencies_ballots_file_path or\
        SUB_CONSTITUENCIES_BALLOTS_PATH
        duckdb_sub_con_ballots_data =\
            duckdb.from_csv_auto(file_path, header=True)
        set_sub_constituencies_ballots_from_sub_con_ballots_file_data(
            duckdb_sub_con_ballots_data=duckdb_sub_con_ballots_data,
            tally=tally,
            command=command,
            logger=logger,
        )

        return len(duckdb_sub_con_ballots_data.fetchall())
    except Exception as e:
        msg =\
            'Error occured while trying to create sub cons and cons: %s' % e
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
        center_code, center_name, center_type, center_lat, center_lon,\
        region_name, office_name, office_number, constituency_name, sc_code,\
        mahalla_name, village_name, _ = row

        constituency = None
        if constituency_name != NO_CONSTITUENCY and\
            sc_code != SPECIAL_VOTING and sc_code != OCV_VOTING:
            try:
                constituency = Constituency.objects.get(
                    name=constituency_name.strip(),
                    tally=tally)
            except (Constituency.DoesNotExist):
                msg = 'Constituency "%s" does not exist' % constituency_name
                if command:
                    command.stdout.write(command.style.WARNING(msg))
                if logger:
                    logger.warning(msg)
                raise Constituency.DoesNotExist(msg)

        sub_constituency = None
        if sc_code == SPECIAL_VOTING or sc_code == OCV_VOTING:
            center_type = CenterType.SPECIAL
        else:
            try:
                sc_code = parse_int(sc_code)
                if sc_code != NO_CONSTITUENCY_SUB_CON_NUMBER:
                    sub_constituency = SubConstituency.objects.get(
                        code=sc_code, tally=tally)
            except (SubConstituency.DoesNotExist):
                sub_constituency = None
                msg = 'SubConstituency "%s" does not exist' % sc_code
                if command:
                    command.stdout.write(command.style.WARNING(msg))
                if logger:
                    logger.warning(msg)
                raise SubConstituency.DoesNotExist(msg)

            center_type = CenterType.GENERAL

        region, _ = Region.objects.get_or_create(
            name=region_name.strip(),
            tally=tally)

        office, _ = Office.objects.get_or_create(
            number=parse_int(office_number),
            name=office_name.strip(),
            tally=tally,
            region=region)

        Center.objects.get_or_create(
            region=region_name,
            code=parse_int(center_code),
            office=office,
            sub_constituency=sub_constituency,
            name=center_name,
            mahalla=mahalla_name,
            village=village_name,
            center_type=center_type,
            longitude=strip_non_numeric(center_lon),
            latitude=strip_non_numeric(center_lat),
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

    # FIXME: For stations whose center name value is `#N/A` we skip them since
    # the centers do not exist in the centers file.
    if center_name == NO_CENTER_NAME_AVAILABLE:
        return

    try:
        center = Center.objects.get(
            code= parse_int(center_code),
            tally=tally)
    except Center.DoesNotExist:
        msg = 'Center "%s" does not exist' % center_code
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Center.DoesNotExist(msg)

    sub_constituency = None
    try:
        if sc_code != SPECIAL_VOTING and sc_code != OCV_VOTING:
            sub_constituency = SubConstituency.objects.get(
                code=parse_int(sc_code), tally=tally)
    except (SubConstituency.DoesNotExist):
        msg = 'SubConstituency "%s" does not exist' % sc_code
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise SubConstituency.DoesNotExist(msg)

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
        electrol_races_by_ballot_name=None,
        ballots_by_ballot_number=None,
        command=None,
        logger=None
):
    try:
        candidate_id, full_name, ballot_number, ballot_name = row
        ballot = ballots_by_ballot_number.get(parse_int(ballot_number))
        if ballot is None:
            raise Ballot.DoesNotExist(
                f'Ballot {ballot_number} does not exist')

        electrol_race = electrol_races_by_ballot_name.get(ballot_name)
        if electrol_race is None:
            raise ElectrolRace.DoesNotExist(
                f'Electrol race {ballot_name} does not exist')

        Candidate.objects.get_or_create(
            ballot=ballot,
            electrol_race=electrol_race,
            candidate_id=candidate_id,
            full_name=full_name,
            order=id_to_ballot_order[candidate_id],
            tally=tally)
    except Exception as e:
        msg = f'error: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)


def import_candidates(command,
                      tally=None,
                      candidates_file=None,
                      ballot_file=None):
    candidates_file_to_parse = candidates_file if candidates_file else open(
        CANDIDATES_PATH, 'r')
    ballot_file_to_parse = ballot_file if ballot_file else open(
        BALLOT_ORDER_PATH, 'r')
    electrol_races_by_ballot_name =\
            {
                electrol_race.ballot_name:\
                electrol_race for electrol_race in\
                    ElectrolRace.objects.filter(tally=tally)
            }
    ballots_by_ballot_number =\
            {
                ballot.number:\
                ballot for ballot in Ballot.objects.filter(tally=tally)
            }

    id_to_ballot_order = {}

    with ballot_file_to_parse as f:
        reader = csv.reader(f)
        next(reader)  # ignore header

        for row in reader:
            candidate_id, order = row
            id_to_ballot_order[candidate_id] = order

    with candidates_file_to_parse as f:
        reader = csv.reader(f)
        next(reader)  # ignore header

        for row in reader:
            process_candidate_row(
                tally,
                row,
                id_to_ballot_order,
                electrol_races_by_ballot_name=electrol_races_by_ballot_name,
                ballots_by_ballot_number=ballots_by_ballot_number,
                command=command)


def process_results_form_row(tally, row, command=None, logger=None):
    replacement_count = 0

    row = empty_strings_to_none(row)
    ballot_number, code, station_number, gender, name,\
        office_name, barcode, serial_number, region_name = row

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
            raise Ballot.DoesNotExist(msg)

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
            raise Center.DoesNotExist(msg)

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
            raise Station.DoesNotExist(msg)

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
                region__name=region_name)
        except Office.DoesNotExist:
            msg = 'Office "%s" does not exist' % office_name
            if command:
                command.stdout.write(command.style.WARNING(msg))
            if logger:
                logger.warning(msg)
            raise Office.DoesNotExist(msg)

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
        form, _ = ResultForm.objects.get_or_create(**kwargs)
        if is_replacement:
            form.is_replacement = is_replacement
            form.save()
    except Exception as e:
        msg = 'Result form could not be created, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

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
        import_candidates(self)

        self.stdout.write(self.style.NOTICE('import result forms'))
        import_result_forms(self)
