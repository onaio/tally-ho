import duckdb
import logging
from django.conf import settings
from tally_ho.apps.tally.management.commands.utils import (
    build_generic_model_key_values_from_duckdb_row_tuple_data,
    check_for_missing_columns,
    get_constituency_by_name,
    get_office_by_office_name_and_region_name,
    get_region_by_name,
    get_sub_constituency_by_code
)
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.region import Region

from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager
from tally_ho.celeryapp import app
from tally_ho.libs.utils.memcache import MemCache

logger = logging.getLogger(__name__)

OCV_VOTING = 'OCV Voting'
SPECIAL_VOTING = 'Special Voting'

def create_regions_from_centers_file_data(
        duckdb_centers_data=None,
        tally=None,
        command=None,
):
    """Create regions from centers csv file data inside duckdb.

    :param duckdb_centers_data: centers csv file data in duckdb format.
    :param tally: regions tally.
    :param command: stdout command.
    :returns: None"""
    try:
        region_col_name =\
            getattr(settings,
                    'REGION_COL_NAME_IN_CENTERS_CSV_FILE')
        regions_data =\
            duckdb_centers_data.project(
            f"{region_col_name}").distinct()
        bulk_mgr = BulkCreateManager(objs_count=regions_data.shape[0])

        for region_row_tuple in regions_data.fetchall():
            kwargs = {}
            kwargs['name'] = region_row_tuple[0]
            if len(kwargs.items()):
                kwargs['tally'] = tally
                bulk_mgr.add(Region(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = f'Failed to create regions, error: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

def create_offices_from_centers_file_data(
        duckdb_centers_data=None,
        regions_by_name=None,
        tally=None,
        command=None,
):
    """Create offices from centers csv file data inside duckdb.

    :param duckdb_centers_data: centers csv file data in duckdb format.
    :param regions_by_name: regions by name.
    :param tally: offices tally.
    :param command: stdout command.
    :returns: None"""
    try:
        office_foreign_key_fields =\
                    ['region']
        col_names_to_model_field_map =\
            getattr(settings,
                    'CENTERS_FILE_COLS_NAMES_TO_OFFICE_MODEL_FIELDS')
        office_cols_names_list =\
            list(col_names_to_model_field_map.keys())
        offices_data =\
                    duckdb_centers_data.project(
                    ','.join(
            office_cols_names_list)).distinct()
        bulk_mgr = BulkCreateManager(
            objs_count=offices_data.shape[0]
        )

        for office_vals_tuple in offices_data.fetchall():
            kwargs =\
                build_generic_model_key_values_from_duckdb_row_tuple_data(
                    office_vals_tuple,
                    col_names_to_model_field_map,
                    office_cols_names_list,
                )
            office_data_by_index =\
                { item[0]: item[1] for item in enumerate(
                list(office_vals_tuple))}
            for index, col_name in enumerate(office_cols_names_list):
                field_name = col_names_to_model_field_map.get(col_name)
                # Continue if field is not a foreign key field
                if field_name not in office_foreign_key_fields:
                    continue

                field_val = office_data_by_index.get(index)
                if field_name == 'region':
                    region = get_region_by_name(
                        field_val,
                        regions_by_name
                    )
                    kwargs['region'] = region
                    continue

            if len(kwargs.items()):
                kwargs['tally'] = tally
                bulk_mgr.add(Office(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = f'Failed to create offices, error: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

def create_centers_from_centers_file_data(
        duckdb_centers_data=None,
        tally=None,
        regions_by_name=None,
        offices_by_name_underscore_region_name=None,
        constituencies_by_name=None,
        sub_constituencies_by_code=None,
        step_name=None,
        step_number=4,
        command=None,
):
    """Create center from centers csv file data inside duckdb.

    :param duckdb_centers_data: centers csv file data in duckdb format.
    :param regions_by_name: regions by name.
    :param tally: centers tally.
    :param offices_by_name_underscore_region_name: office by name
        underscore region name.
    :param constituencies_by_name: constituencies by name.
    :param sub_constituencies_by_code: sub constituencies by code.
    :param step_name: step name.
    :param step_number: step number.
    :param command: stdout command.
    :returns: None"""
    try:
        instances_count_memcache_key =\
            f"{tally.id}_{step_name}_{step_number}"
        # reset instances count in memcache if exists already
        client = MemCache()
        client.delete(instances_count_memcache_key)
        centers_foreign_key_fields =\
                    ['region', 'office', 'constituency',
                     'sub_constituency', 'center_type']
        col_names_to_model_field_map =\
            getattr(settings,
                    'CENTERS_FILE_COLS_NAMES_TO_CENTER_MODEL_FIELDS')
        center_cols_names_list =\
            list(col_names_to_model_field_map.keys())
        centers_data =\
                    duckdb_centers_data.project(
                    ','.join(
            center_cols_names_list)).distinct().fetchall()
        bulk_mgr = BulkCreateManager(
            cache_instances_count=True,
            cache_key=instances_count_memcache_key
        )

        for center_vals_tuple in centers_data:
            kwargs =\
                build_generic_model_key_values_from_duckdb_row_tuple_data(
                    center_vals_tuple,
                    col_names_to_model_field_map,
                    center_cols_names_list,
                )
            center_data_by_index =\
                { item[0]: item[1] for item in enumerate(
                list(center_vals_tuple))}
            for index, col_name in enumerate(center_cols_names_list):
                field_name = col_names_to_model_field_map.get(col_name)
                # Continue if field is not a foreign key field
                if field_name not in centers_foreign_key_fields:
                    continue

                field_val = center_data_by_index.get(index)
                if field_name == 'office':
                    office = get_office_by_office_name_and_region_name(
                        field_val,
                        kwargs.get('region'),
                        offices_by_name_underscore_region_name
                    )
                    kwargs['office'] = office
                    continue

                if field_name == 'region':
                    region = get_region_by_name(
                        field_val,
                        regions_by_name
                    )
                    kwargs['region'] = region
                    continue

                if field_name == 'center_type':
                    sc_code = kwargs.get('sub_constituency')
                    kwargs['center_type'] =\
                        CenterType.SPECIAL if sc_code == SPECIAL_VOTING or\
                            sc_code == OCV_VOTING else CenterType.GENERAL
                    continue

                if field_name == 'constituency':
                    constituency = get_constituency_by_name(
                        field_val,
                        constituencies_by_name,
                        kwargs.get('sub_constituency')
                    )
                    kwargs['constituency'] = constituency
                    continue

                if field_name == 'sub_constituency':
                    sub_con = get_sub_constituency_by_code(
                        field_val,
                        sub_constituencies_by_code
                    )
                    kwargs['sub_constituency'] = sub_con
                    continue

            if len(kwargs.items()):
                kwargs['tally'] = tally
                bulk_mgr.add(Center(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = f'Failed to create centers, error: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

@app.task()
def async_import_centers_from_centers_file(
        tally_id=None,
        csv_file_path=None,
        command=None,
        **kwargs):
    """Create centers from a centers csv file.

    :param tally_id: tally id.
    :param csv_file_path: centers csv file path.
    :param command: stdout command.
    :returns: candidates count."""
    try:
        tally = Tally.objects.get(id=tally_id)
        centers_file_path = csv_file_path
        duckdb_centers_data =\
            duckdb.from_csv_auto(centers_file_path, header=True).distinct()
        center_col_names =\
            getattr(settings,
                    'CENTER_COLUMN_NAMES')
        check_for_missing_columns(
            center_col_names,
            duckdb_centers_data.columns,
            'centers'
        )
        create_regions_from_centers_file_data(
            duckdb_centers_data=duckdb_centers_data,
            tally=tally,
            command=command,
        )
        regions_by_name =\
            {
                region.name:\
                region for region in Region.objects.filter(tally=tally)
            }
        create_offices_from_centers_file_data(
            duckdb_centers_data=duckdb_centers_data,
            regions_by_name=regions_by_name,
            tally=tally,
            command=command,
        )
        offices_by_name_underscore_region_name =\
            {
                f'{office.name}_{office.region.name}':\
                office for office in Office.objects.filter(tally=tally)
            }
        constituencies_by_name =\
            {
                constituency.name:\
                constituency for constituency in\
                    Constituency.objects.filter(
                            tally=tally)
            }
        sub_constituencies_by_code =\
            {
                sub_constituency.code:\
                sub_constituency for sub_constituency in\
                    SubConstituency.objects.filter(
                            tally=tally)
            }
        create_centers_from_centers_file_data(
            duckdb_centers_data=duckdb_centers_data,
            tally=tally,
            regions_by_name=regions_by_name,
            offices_by_name_underscore_region_name=
            offices_by_name_underscore_region_name,
            constituencies_by_name=constituencies_by_name,
            sub_constituencies_by_code=sub_constituencies_by_code,
            step_name=kwargs.get('step_name'),
            step_number=kwargs.get('step_number'),
            command=command,
        )

        return duckdb_centers_data.shape[0]
    except Exception as e:
        msg = f'Error occured while trying to create centers: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)
