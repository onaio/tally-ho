import duckdb
from gettext import ngettext
from django.conf import settings
from django.db import transaction

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.utils.numbers import parse_int

OCV_VOTING = 'OCV Voting'
SPECIAL_VOTING = 'Special Voting'
NO_CONSTITUENCY = 'No Constituency'
NO_CONSTITUENCY_SUB_CON_NUMBER = 999

NO_CENTER_NAME_AVAILABLE = '#N/A'

def build_generic_model_key_values_from_duckdb_row_tuple_data(
        duckdb_row_tuple_data,
        col_name_to_model_field_mapping,
        file_col_names_list
    ):
    """
    Build a key,value list of dictionaries, the key as the model name and
    respective fied value. This kwargs are for generic model fields
    that do not include many to many fields or foreign fields.

    param: duckdb_row_tuple_data: duckdb row tuple data
    param: col_name_to_model_field_mapping: column name to model field mapping
    param: file_col_names_list: file column names list
    :returns: kwargs.
    """
    kwargs = {}
    tuple_data_by_index =\
        { item[0]: item[1] for item in enumerate(
        list(duckdb_row_tuple_data))}
    for index, col_name in enumerate(file_col_names_list):
        field_name = col_name_to_model_field_mapping.get(col_name)
        field_val = tuple_data_by_index.get(index)
        if field_val:
            kwargs[field_name] =\
                parse_int(field_val)\
                    if parse_int(field_val) else field_val
    return kwargs

def generate_duckdb_electrol_race_str_query(electrol_race=None):
    """Generate string query for querying electrol race columns
    in ballots file using duckdb.

    :param electrol_race: electrol race queryset.
    :returns: string query."""
    col_names_to_model_field_map =\
            getattr(settings,
                    'BALLOT_COLS_TO_ELECTROL_RACE_MODEL_FIELDS_MAPPING')
    str_query = None
    for column_name in\
            list(col_names_to_model_field_map.keys()):
            electrol_race_field_name =\
                col_names_to_model_field_map.get(
                column_name
            )
            electrol_race_field_val =\
                getattr(electrol_race, electrol_race_field_name)

            if str_query is None:
                str_query =\
                    f" {column_name}" +\
                    f" = '{electrol_race_field_val}'"
            else:
                str_query +=\
                    f" AND {column_name}" +\
                    f" = '{electrol_race_field_val}'"

    return str_query

def get_region_by_name(
        region_name,
        regions_by_name,
    ):
    region =\
        regions_by_name.get(region_name)
    if region is None:
        raise Region.DoesNotExist(f'Region {region_name} does not ')

    return region

def get_office_by_office_name_and_region_name(
        office_name,
        region_name,
        offices_by_name_underscore_region_name,
    ):
    office = None
    if office_name and region_name:
        office =\
            offices_by_name_underscore_region_name.get(
                    f"{office_name.strip()}_{region_name}")
        if office is None:
            raise Office.DoesNotExist(
                str(f'Office {office_name} does not '
                    f'exist for region {region_name}'))

    return office

def get_constituency_by_name(
        constituency_name,
        constituency_by_name,
        sc_code,
    ):
    constituency = None
    if constituency_name != NO_CONSTITUENCY and\
            sc_code != SPECIAL_VOTING and sc_code != OCV_VOTING:
        constituency =\
            constituency_by_name.get(constituency_name)
        if constituency is None:
            raise Constituency.DoesNotExist(
                f'Constituency {constituency_name} does not exist')

    return constituency

def get_sub_constituency_by_code(
        sc_code,
        sc_by_code,
    ):
    sub_constituency = None
    sc_code = parse_int(sc_code)
    if sc_code and sc_code != SPECIAL_VOTING and sc_code != OCV_VOTING\
        and sc_code != NO_CONSTITUENCY_SUB_CON_NUMBER:
        sub_constituency =\
            sc_by_code.get(sc_code)
        if sub_constituency is None:
            raise SubConstituency.DoesNotExist(
                f'SubConstituency {sc_code} does not exist')

    return sub_constituency

def get_center_by_center_code(
        center_code,
        centers_by_code,
    ):
    center = None
    center_code = parse_int(center_code)
    if center_code:
        center =\
            centers_by_code.get(center_code)
        if center is None:
            raise Center.DoesNotExist(
                f'Center {center_code} does not exist')

    return center

def get_ballot_by_ballot_number(
        ballot_number,
        ballots_by_ballot_number,
    ):
    ballot = ballots_by_ballot_number.get(parse_int(ballot_number))
    if ballot is None:
        raise Ballot.DoesNotExist(
            f'Ballot {ballot_number} does not exist')

    return ballot

def get_electrol_race_by_ballot_name(
        ballot_name,
        electrol_races_by_ballot_name,
    ):
    electrol_race = electrol_races_by_ballot_name.get(ballot_name)
    if electrol_race is None:
        raise ElectrolRace.DoesNotExist(
            f'Electrol race with sub race {ballot_name} does not exist')

    return electrol_race

def delete_all_tally_objects(tally):
    """
    Delete all tally objects.

    :param tally: The tally for filtering objects to delete.
    """
    with transaction.atomic():
        ResultForm.objects.filter(tally=tally).delete()
        Candidate.objects.filter(tally=tally).delete()
        Station.objects.filter(tally=tally).delete()
        Center.objects.filter(tally=tally).delete()
        SubConstituency.objects.filter(tally=tally).delete()
        Constituency.objects.filter(tally=tally).delete()
        Ballot.objects.filter(tally=tally).delete()
        Office.objects.filter(tally=tally).delete()
        Region.objects.filter(tally=tally).delete()
        ElectrolRace.objects.filter(tally=tally).delete()

def find_missing_csv_col_names(
        required_col_names_list,
        csv_file_col_names_list
    ):
    return [name for name in required_col_names_list\
            if name not in csv_file_col_names_list]

def check_for_missing_columns(
        required_col_names_list,
        csv_file_col_names_list,
        file_name
    ):
    missing_columns =\
            find_missing_csv_col_names(
                required_col_names_list, csv_file_col_names_list)
    if len(missing_columns):
        str_m_cols = ', '.join(missing_columns)
        error_message =\
            ngettext(
                f'Column {str_m_cols} is missing in the {file_name} file',
                f'Columns {str_m_cols} are missing in the {file_name} file',
                len(missing_columns)
            )
        raise Exception(error_message)
    return None

class DuplicateFoundError(Exception):
    """Custom exception to be raised when duplicates are found."""
    pass

def check_duplicates(csv_file_path: str, field: str) -> None:
    """
    Checks for duplicates in a CSV file based on a specified field using
    DuckDB.

    This function loads the specified CSV file into DuckDB, groups the data
    by the provided field, and checks if any of the groups contain more than
    one row. It returns `True` if duplicates are found, otherwise `False`.

    Parameters:
    ----------
    csv_file_path : str
        The path to the CSV file to be checked.
    field : str, optional
        The name of the field/column to check for duplicates.

    Raises:
    -------
    DuplicatesFoundError
        If duplicates are found in the specified field.

    Returns:
    -------
    None
        If no duplicates are found.
    """
    con = duckdb.connect()

    result = con.execute(f"""
        SELECT {field}, COUNT(*) AS cnt
        FROM read_csv_auto('{csv_file_path}')
        GROUP BY {field}
        HAVING cnt > 1
    """).fetchall()

    if len(result) > 0:
        raise DuplicateFoundError(f"Duplicates found for field '{field}'")
