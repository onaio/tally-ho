import duckdb
import logging

from django.conf import settings
from tally_ho.apps.tally.management.commands.utils import (
    build_generic_model_key_values_from_duckdb_row_tuple_data,
    check_duplicates,
    check_for_missing_columns,
    get_ballot_by_ballot_number,
    get_office_by_office_name_and_region_name,
)
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.utils.numbers import parse_int
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager
from tally_ho.celeryapp import app
from tally_ho.libs.utils.memcache import MemCache

logger = logging.getLogger(__name__)

def get_result_form_center(
        center_code,
        result_form_station_number,
        centers_by_code,
        stations_by_number_underscore_center_code
    ):
    center = None
    center_code = parse_int(center_code)
    if center_code:
        center =\
            centers_by_code.get(center_code)
        if center is None:
            raise Center.DoesNotExist(
                f'Center {center_code} does not exist')
        station =\
            stations_by_number_underscore_center_code.get(
            f"{center_code}_{result_form_station_number}"
            )
        if station is None:
            msg =\
                str(f'Station {result_form_station_number} does not exist '
                    f'for center {center_code}')
            raise Station.DoesNotExist(msg)

    return center

def create_result_forms_result_form_file_data(
        duckdb_result_forms_data=None,
        tally=None,
        ballots_by_ballot_number=None,
        centers_by_code=None,
        offices_by_name_underscore_region_name=None,
        stations_by_number_underscore_center_code=None,
        step_number=7,
        step_name=None,
        command=None,
):
    """Create result forms from result forms file data inside duckdb.

    :param duckdb_result_forms_data: result forms file data in duckdb format.
    :param tally: result forms tally.
    :param ballots_by_ballot_number: ballots by ballot number dictionary.
    :param centers_by_code: centers by code dictionary.
    :param offices_by_name_underscore_region_name: offices by office name
    underscore region name.
    :param stations_by_number_underscore_center_code: stations by station
    number underscore center code.
    :param step_number: Step number
    :param step_name: Step name
    :param command: stdout command.
    :returns: None"""
    try:
        instances_count_memcache_key =\
            f"{tally.id}_{step_name}_{step_number}"
        # reset instances count in memcache if exists already
        client = MemCache()
        client.delete(instances_count_memcache_key)
        genders_by_name =\
            {
                gender.name: gender for gender in Gender\
                    if gender.name != 'CHOICES'
            }
        result_form_foreign_key_fields =\
                    ['center', 'office', 'ballot', 'gender']
        col_names_to_model_field_map =\
            getattr(settings,
                    'RESULT_FORM_FILE_COLS_NAMES_TO_RESULT_FORM_MODEL_FIELDS')
        result_forms_cols_names_list =\
            list(col_names_to_model_field_map.keys())
        result_forms_data =\
                    duckdb_result_forms_data.project(
                    ','.join(
            result_forms_cols_names_list)).distinct().fetchall()
        bulk_mgr = BulkCreateManager(
            chunk_size=1000,
            cache_instances_count=True,
            cache_key=instances_count_memcache_key,
            memcache_client=client,
        )

        for result_form_vals_tuple in result_forms_data:
            kwargs =\
                build_generic_model_key_values_from_duckdb_row_tuple_data(
                    result_form_vals_tuple,
                    col_names_to_model_field_map,
                    result_forms_cols_names_list,
                )
            result_form_data_by_index =\
                { item[0]: item[1] for item in enumerate(
                list(result_form_vals_tuple))}
            for index, col_name in enumerate(result_forms_cols_names_list):
                field_name = col_names_to_model_field_map.get(col_name)
                # Continue if field is not a foreign key field
                if field_name not in result_form_foreign_key_fields:
                    continue

                field_val = result_form_data_by_index.get(index)
                if field_name == 'center':
                    center = get_result_form_center(
                        field_val,
                        kwargs.get('station_number'),
                        centers_by_code,
                        stations_by_number_underscore_center_code
                    )
                    if center is None:
                        kwargs['is_replacement'] = True
                    kwargs['center'] = center
                    continue

                if field_name == 'office':
                    result_form_region_name = kwargs.get('region')
                    if result_form_region_name:
                        del kwargs['region']
                    office = get_office_by_office_name_and_region_name(
                        field_val,
                        result_form_region_name,
                        offices_by_name_underscore_region_name
                    )
                    kwargs['office'] = office
                    continue

                if field_name == 'ballot':
                    kwargs['ballot'] =\
                        get_ballot_by_ballot_number(
                            field_val,
                            ballots_by_ballot_number
                        )
                    continue

                if field_name == 'gender':
                    kwargs['gender'] = genders_by_name.get(field_val.upper())
                    continue

            if len(kwargs.items()):
                kwargs['tally'] = tally
                kwargs['form_state'] = FormState.UNSUBMITTED
                bulk_mgr.add(ResultForm(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = 'Failed to create result forms, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

@app.task()
def async_import_results_forms_from_result_forms_file(
        tally_id=None,
        csv_file_path=None,
        command=None,
        **kwargs):
    """Create result forms from a result forms csv file.

    :param tally_id: tally id.
    :param csv_file_path: result forms csv file path.
    :param command: stdout command.
    :returns: Result forms count."""
    try:
        tally = Tally.objects.get(id=tally_id)
        file_path = csv_file_path
        duckdb_result_forms_data = duckdb.from_csv_auto(file_path, header=True)
        result_forms_col_names =\
            getattr(settings,
                    'RESULT_FORM_COLUMN_NAMES')
        check_for_missing_columns(
            result_forms_col_names,
            duckdb_result_forms_data.columns,
            'result_form'
        )
        check_duplicates(
            csv_file_path=file_path,
            field='barcode'
        )

        stations_by_number_underscore_center_code =\
            {
                f'{station.center.code}_{station.station_number}':\
                station for station in Station.objects.filter(tally=tally)
            }
        ballots_by_ballot_number =\
            {
                ballot.number:\
                ballot for ballot in Ballot.objects.filter(tally=tally)
            }
        centers_by_code =\
            {
                center.code:\
                center for center in Center.objects.filter(tally=tally)
            }
        offices_by_name_underscore_region_name =\
            {
                f'{office.name}_{office.region.name}':\
                office for office in Office.objects.filter(tally=tally)
            }
        create_result_forms_result_form_file_data(
            duckdb_result_forms_data=duckdb_result_forms_data,
            tally=tally,
            ballots_by_ballot_number=ballots_by_ballot_number,
            centers_by_code=centers_by_code,
            offices_by_name_underscore_region_name=
            offices_by_name_underscore_region_name,
            stations_by_number_underscore_center_code=
            stations_by_number_underscore_center_code,
            step_name=kwargs.get('step_name'),
            step_number=kwargs.get('step_number'),
            command=command,
        )

        return duckdb_result_forms_data.shape[0]
    except Exception as e:
        msg = f'Error occured while trying to create result forms: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)
