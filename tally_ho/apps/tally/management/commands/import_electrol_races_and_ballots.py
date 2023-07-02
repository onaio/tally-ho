import duckdb
import logging
from django.conf import settings
from tally_ho.apps.tally.models.ballot import Ballot

from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.management.commands.utils import (
    build_generic_model_key_values_from_duckdb_row_tuple_data,
    check_for_missing_columns,
    generate_duckdb_electrol_race_str_query
)
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.utils.numbers import parse_int
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager
from tally_ho.celeryapp import app
from tally_ho.libs.utils.memcache import MemCache

logger = logging.getLogger(__name__)


def create_electrol_races_from_ballot_file_data(
        duckdb_ballots_data=None,
        tally=None,
        command=None,
):
    """Create electrol races from ballot file data inside duckdb.

    :param duckdb_ballots_data: Ballot file data in duckdb format.
    :param tally: Electrol races tally.
    :param command: stdout command.
    :returns: None"""
    try:
        col_names_to_model_field_map =\
            getattr(settings,
                    'BALLOT_COLS_TO_ELECTROL_RACE_MODEL_FIELDS_MAPPING')
        electrol_races_cols_list =\
            list(col_names_to_model_field_map.keys())
        electrol_races_data =\
            duckdb_ballots_data.project(
            ','.join(electrol_races_cols_list)).distinct().fetchall()
        bulk_mgr = BulkCreateManager(objs_count=len(electrol_races_data))

        for electrol_race_row_tuple in electrol_races_data:
            kwargs =\
                build_generic_model_key_values_from_duckdb_row_tuple_data(
                    electrol_race_row_tuple,
                    col_names_to_model_field_map,
                    electrol_races_cols_list,
                )
            if len(kwargs.items()):
                kwargs['tally'] = tally
                bulk_mgr.add(ElectrolRace(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = 'Failed to create electrol races, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

def create_ballots_from_ballot_file_data(
        duckdb_ballots_data=None,
        electrol_races=None,
        tally=None,
        command=None,
        instances_count_memcache_key=None,
        memcache_client=None,
):
    """Create ballots from ballot file data inside duckdb.

    :param duckdb_ballots_data: Ballot file data in duckdb format.
    :param electrol_races: Tally electrol races queryset.
    :param tally: tally queryset.
    :param instances_count_memcache_key: instances count memcache key.
    :param memcache_client: memcache client.
    :param command: stdout command.
    :returns: None."""
    try:
        bulk_mgr = BulkCreateManager(
            objs_count=len(duckdb_ballots_data.distinct().fetchall()),
            cache_instances_count=True,
            cache_key=instances_count_memcache_key,
            memcache_client=memcache_client,)
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
                # TODO: Some ballot numbers are in string format we need to
                # figure out how they should be handled here.
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
        raise Exception(msg)

@app.task()
def async_import_electrol_races_and_ballots_from_ballots_file(
        tally_id=None,
        csv_file_path=None,
        command=None,
        **kwargs
    ):
    """Create electrol races and ballots from a ballots csv file.

    :param tally_id: tally id.
    :param csv_file_path: ballots csv file path.
    :param command: stdout command.
    :returns: Ballots count."""
    try:
        tally = Tally.objects.get(id=tally_id)
        step_number = kwargs.get('step_number')
        step_name=kwargs.get('step_name')
        instances_count_memcache_key =\
            f"{tally.id}_{step_name}_{step_number}"
        # reset instances count in memcache if exists already
        memcache_client = MemCache()
        memcache_client.delete(instances_count_memcache_key)

        ballots_data = duckdb.from_csv_auto(csv_file_path, header=True)
        ballots_col_names =\
            getattr(settings,
                    'BALLOT_COLUMN_NAMES')
        check_for_missing_columns(
            ballots_col_names,
            ballots_data.columns,
            'ballots'
        )
        create_electrol_races_from_ballot_file_data(
            duckdb_ballots_data=ballots_data,
            tally=tally,
            command=command,
        )
        electrol_races = ElectrolRace.objects.filter(tally=tally)

        create_ballots_from_ballot_file_data(
            duckdb_ballots_data=ballots_data,
            electrol_races=electrol_races,
            tally=tally,
            command=command,
            instances_count_memcache_key=instances_count_memcache_key,
            memcache_client=memcache_client
        )

        return len(ballots_data.fetchall())
    except Exception as e:
        msg = 'Error occured while trying to create ballots: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)
