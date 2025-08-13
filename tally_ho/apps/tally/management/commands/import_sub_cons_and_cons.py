import logging

import duckdb
from django.conf import settings

from tally_ho.apps.tally.management.commands.utils import (
    build_generic_model_key_values_from_duckdb_row_tuple_data,
    check_for_missing_columns,
)
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.celeryapp import app
from tally_ho.libs.utils.memcache import MemCache
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager

logger = logging.getLogger(__name__)

def create_sub_constituencies_from_sub_con_file_data(
        duckdb_sub_con_data=None,
        constituencies_by_name=None,
        tally=None,
        command=None,
        instances_count_memcache_key=None,
        memcache_client=None,
):
    """Create sub constituencies from sub constituencies file data
        inside duckdb.

    :param duckdb_sub_con_data: sub constituencies file data in duckdb format.
    :param constituencies_by_name: tally constituencies_by_name queryset.
    :param tally: tally queryset.
    :param instances_count_memcache_key: instances count memcache key.
    :param memcache_client: memcache client.
    :param command: stdout command.
    :returns: None."""
    try:
        col_names_to_model_field_map =\
            settings.SUB_CON_FILE_COLS_NAMES_TO_SUB_CON_MODEL_FIELDS
        sub_con_cols_names_list = list(col_names_to_model_field_map.keys())
        sub_cons_data =\
                    duckdb_sub_con_data.project(
                    ','.join(sub_con_cols_names_list)).distinct().fetchall()
        bulk_mgr = BulkCreateManager(
            objs_count=len(sub_cons_data),
            cache_instances_count=True,
            cache_key=instances_count_memcache_key,
            memcache_client=memcache_client,)

        for sub_con_vals_tuple in sub_cons_data:
            kwargs =\
                build_generic_model_key_values_from_duckdb_row_tuple_data(
                    sub_con_vals_tuple,
                    col_names_to_model_field_map,
                    sub_con_cols_names_list,
                )
            sub_con_data_by_index =\
                { item[0]: item[1] for item in enumerate(
                list(sub_con_vals_tuple))}
            for index, col_name in enumerate(sub_con_cols_names_list):
                field_name = col_names_to_model_field_map.get(col_name)
                field_val = sub_con_data_by_index.get(index)
                if field_name == 'constituency':
                    kwargs['constituency'] =\
                        constituencies_by_name.get(field_val)

            if len(kwargs.items()):
                kwargs['tally'] = tally
                bulk_mgr.add(SubConstituency(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = 'Failed to create sub constituencies, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

def create_constituencies_from_sub_con_file_data(
        duckdb_sub_con_data=None,
        tally=None,
        command=None,
):
    """Create constituencies from sub constituencies file data inside duckdb.

    :param duckdb_sub_con_data: sub constituencies file data in duckdb format.
    :param tally: tally queryset.
    :param command: stdout command.
    :returns: None."""
    try:
        constituency_column_name =\
            settings.CONSTITUENCY_COLUMN_NAME_IN_SUB_CONSTITUENCY_FILE
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
        raise Exception(msg)

@app.task()
def async_import_sub_constituencies_and_constituencies_from_sub_cons_file(
        tally_id=None,
        csv_file_path=None,
        command=None,
        **kwargs):
    """Create sub constituencies and constituencies from a sub constituencies
    csv file.

    :param tally_id: tally id.
    :param csv_file_path: sub constituencies csv file path.
    :param command: stdout command.
    :returns: Sub Constituencies count."""
    try:
        tally = Tally.objects.get(id=tally_id)
        step_number = kwargs.get('step_number')
        step_name=kwargs.get('step_name')
        instances_count_memcache_key =\
            f"{tally.id}_{step_name}_{step_number}"
        # reset instances count in memcache if exists already
        memcache_client = MemCache()
        memcache_client.delete(instances_count_memcache_key)
        duckdb_sub_con_data = duckdb.from_csv_auto(csv_file_path, header=True)
        sub_cons_col_names =\
            settings.SUB_CONSTITUENCY_COLUMN_NAMES
        check_for_missing_columns(
            sub_cons_col_names,
            duckdb_sub_con_data.columns,
            'sub constituencies'
        )
        create_constituencies_from_sub_con_file_data(
            duckdb_sub_con_data=duckdb_sub_con_data,
            tally=tally,
            command=command,
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
            instances_count_memcache_key=instances_count_memcache_key,
            memcache_client=memcache_client
        )

        return len(duckdb_sub_con_data.fetchall())
    except Exception as e:
        msg =\
            'Error occured while trying to create sub cons and cons: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)
