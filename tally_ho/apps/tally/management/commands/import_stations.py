import duckdb
import logging

from django.conf import settings

from tally_ho.apps.tally.management.commands.utils import (
    build_generic_model_key_values_from_duckdb_row_tuple_data,
    check_for_missing_columns,
    get_center_by_center_code,
    get_sub_constituency_by_code
)
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager
from tally_ho.celeryapp import app
from tally_ho.libs.utils.memcache import MemCache

logger = logging.getLogger(__name__)

NO_CENTER_NAME_AVAILABLE = '#N/A'

def create_stations_from_stations_file_data(
        duckdb_stations_data=None,
        tally=None,
        sub_cons_by_code=None,
        centers_by_code=None,
        step_number=7,
        step_name=None,
        command=None,
):
    """Create stations from stations file data inside duckdb.

    :param duckdb_stations_data: stations file data in duckdb format.
    :param tally: stations tally.
    :param sub_cons_by_code: sub cons by code dictionary.
    :param centers_by_code: centers by code dictionary.
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
        station_foreign_key_fields =\
                    ['center', 'sub_constituency', 'gender']
        col_names_to_model_field_map =\
            getattr(settings,
                    'STATIONS_FILE_COLS_NAMES_TO_STATION_MODEL_FIELDS')
        stations_cols_names_list =\
            list(col_names_to_model_field_map.keys())
        stations_data =\
                    duckdb_stations_data.project(
                    ','.join(
            stations_cols_names_list)).filter(
            f"center_name != '{NO_CENTER_NAME_AVAILABLE}'").distinct(
            ).fetchall()
        bulk_mgr = BulkCreateManager(
            chunk_size=1000,
            cache_instances_count=True,
            cache_key=instances_count_memcache_key,
            memcache_client=client,
        )

        for station_vals_tuple in stations_data:
            kwargs =\
                build_generic_model_key_values_from_duckdb_row_tuple_data(
                    station_vals_tuple,
                    col_names_to_model_field_map,
                    stations_cols_names_list,
                )
            station_data_by_index =\
                { item[0]: item[1] for item in enumerate(
                list(station_vals_tuple))}
            for index, col_name in enumerate(stations_cols_names_list):
                field_name = col_names_to_model_field_map.get(col_name)
                # Continue if field is not a foreign key field
                if field_name not in station_foreign_key_fields:
                    continue

                field_val = station_data_by_index.get(index)
                if field_name == 'center':
                    center = get_center_by_center_code(
                        field_val,
                        centers_by_code
                    )
                    kwargs['center'] = center
                    continue

                if field_name == 'sub_constituency':
                    sub_constituency = get_sub_constituency_by_code(
                        field_val,
                        sub_cons_by_code,
                    )
                    kwargs['sub_constituency'] = sub_constituency
                    continue

                if field_name == 'gender':
                    kwargs['gender'] = genders_by_name.get(field_val.upper())
                    continue

            if len(kwargs.items()):
                kwargs['tally'] = tally
                del kwargs['center_name']
                bulk_mgr.add(Station(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = f'Failed to create stations, error: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

@app.task()
def async_import_stations_from_stations_file(
        tally_id=None,
        csv_file_path=None,
        command=None,
        **kwargs):
    """Create stations from a stations csv file.

    :param tally_id: tally id.
    :param csv_file_path: stations csv file path.
    :param command: stdout command.
    :returns: stations count."""
    try:
        tally = Tally.objects.get(id=tally_id)
        file_path = csv_file_path
        duckdb_stations_data = duckdb.from_csv_auto(file_path, header=True)
        stations_col_names =\
            getattr(settings,
                    'STATION_COLUMN_NAMES')
        check_for_missing_columns(
            stations_col_names,
            duckdb_stations_data.columns,
            'stations'
        )
        centers_by_code =\
            {
                center.code:\
                center for center in Center.objects.filter(tally=tally)
            }
        sub_cons_by_code =\
            {
                sc.code:\
                sc for sc in SubConstituency.objects.filter(tally=tally)
            }
        create_stations_from_stations_file_data(
            duckdb_stations_data=duckdb_stations_data,
            tally=tally,
            sub_cons_by_code=sub_cons_by_code,
            centers_by_code=centers_by_code,
            step_name=kwargs.get('step_name'),
            step_number=kwargs.get('step_number'),
            command=command,
        )

        return duckdb_stations_data.shape[0]
    except Exception as e:
        msg = f'Error occured while trying to create stations: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)
