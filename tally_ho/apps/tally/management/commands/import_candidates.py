import duckdb
import logging

from django.conf import settings
from tally_ho.apps.tally.management.commands.utils import (
    build_generic_model_key_values_from_duckdb_row_tuple_data,
    check_for_missing_columns,
    get_ballot_by_ballot_number,
    get_electrol_race_by_ballot_name,
)
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.utils.query_set_helpers import BulkCreateManager
from tally_ho.celeryapp import app
from tally_ho.libs.utils.memcache import MemCache

logger = logging.getLogger(__name__)

def create_candidates_from_candidates_file_data(
        duckdb_candidates_data=None,
        tally=None,
        ballots_by_ballot_number=None,
        electrol_races_by_ballot_name=None,
        candidate_id_by_ballot_order_dict=None,
        step_number=None,
        step_name=None,
        command=None,
):
    """Create candidates from candidates file data inside duckdb.

    :param duckdb_candidates_data: candidates file data in duckdb format.
    :param tally: candidates tally.
    :param ballots_by_ballot_number: ballots by ballot name dict.
    :param electrol_races_by_ballot_name: electrol races by ballot name dict.
    :param candidate_id_by_ballot_order_dict: candidate id by ballot order
        dict.
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
        candidate_foreign_key_fields =\
                    ['ballot', 'electrol_race']
        col_names_to_model_field_map =\
            getattr(settings,
                    'CANDIDATE_FILE_COLS_NAMES_TO_CANDIDATE_MODEL_FIELDS')
        candidates_cols_names_list =\
            list(col_names_to_model_field_map.keys())
        candidates_data =\
                    duckdb_candidates_data.project(
                    ','.join(
            candidates_cols_names_list)).distinct().fetchall()
        bulk_mgr = BulkCreateManager(
            chunk_size=1000,
            cache_instances_count=True,
            cache_key=instances_count_memcache_key,
            memcache_client=client,
        )

        for candidate_vals_tuple in candidates_data:
            kwargs =\
                build_generic_model_key_values_from_duckdb_row_tuple_data(
                    candidate_vals_tuple,
                    col_names_to_model_field_map,
                    candidates_cols_names_list,
                )
            candidate_data_by_index =\
                { item[0]: item[1] for item in enumerate(
                list(candidate_vals_tuple))}
            for index, col_name in enumerate(candidates_cols_names_list):
                field_name = col_names_to_model_field_map.get(col_name)
                # Continue if field is not a foreign key field
                if field_name not in candidate_foreign_key_fields:
                    continue

                field_val = candidate_data_by_index.get(index)
                if field_name == 'ballot':
                    ballot = get_ballot_by_ballot_number(
                        field_val,
                        ballots_by_ballot_number
                    )
                    kwargs['ballot'] = ballot
                    continue

                if field_name == 'electrol_race':
                    electrol_race = get_electrol_race_by_ballot_name(
                        field_val,
                        electrol_races_by_ballot_name,
                    )
                    kwargs['electrol_race'] = electrol_race
                    continue

            if len(kwargs.items()):
                kwargs['tally'] = tally
                kwargs['order'] = candidate_id_by_ballot_order_dict.get(
                    kwargs.get('candidate_id'))
                bulk_mgr.add(Candidate(**kwargs))
        bulk_mgr.done()

        return
    except Exception as e:
        msg = 'Failed to create candidates, error: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)

def build_candidate_id_by_ballot_order_dict(ballot_order_file_path):
    """
    Builds a dictionary of candidate id by ballot order from the ballot order
    to candidates ids csv file.

    :param ballot_order_file_path: ballot order to candidates ids csv file.
    :returns: candidate ids by ballot order dictionary or error exception.
    """
    try:
        candidate_id_by_ballot_order = {}
        ballot_order_column_list =\
                getattr(settings,
                        'BALLOT_ORDER_COLUMN_NAMES')
        duckdb_ballot_order_data =\
            duckdb.from_csv_auto(ballot_order_file_path, header=True).project(
                    ','.join(
            ballot_order_column_list)).distinct().fetchall()
        candidate_id_by_ballot_order =\
            { item[0]: item[1] for item in duckdb_ballot_order_data }
        return candidate_id_by_ballot_order
    except Exception as e:
        msg = str("Error occured while generating candidate id to"
                  f"ballot order dictionary, error: {e}")
        raise Exception(msg)

@app.task()
def async_import_candidates_from_candidates_file(
        tally_id=None,
        csv_file_path=None,
        command=None,
        **kwargs):
    """Create candidates from a candidates csv file.

    :param tally_id: tally id.
    :param csv_file_path: candidates csv file path.
    :param command: stdout command.
    :returns: candidates count."""
    try:
        tally = Tally.objects.get(id=tally_id)
        candidates_file_path = csv_file_path
        duckdb_candidates_data =\
            duckdb.from_csv_auto(candidates_file_path, header=True)
        candidate_col_names =\
            getattr(settings,
                    'CANDIDATE_COLUMN_NAMES')
        check_for_missing_columns(
            candidate_col_names,
            duckdb_candidates_data.columns,
            'candidates'
        )
        ballot_order_file_path = kwargs.get('ballot_order_file_path')
        candidate_id_by_ballot_order_dict =\
            build_candidate_id_by_ballot_order_dict(
                ballot_order_file_path
            )
        ballots_by_ballot_number =\
            {
                ballot.number:\
                ballot for ballot in Ballot.objects.filter(tally=tally)
            }
        electrol_races_by_ballot_name =\
            {
                electrol_race.ballot_name:\
                electrol_race for electrol_race in\
                    ElectrolRace.objects.filter(tally=tally)
            }
        create_candidates_from_candidates_file_data(
            duckdb_candidates_data=duckdb_candidates_data,
            tally=tally,
            ballots_by_ballot_number=ballots_by_ballot_number,
            electrol_races_by_ballot_name=electrol_races_by_ballot_name,
            candidate_id_by_ballot_order_dict=
            candidate_id_by_ballot_order_dict,
            step_name=kwargs.get('step_name'),
            step_number=kwargs.get('step_number'),
            command=command,
        )

        return duckdb_candidates_data.shape[0]
    except Exception as e:
        msg = f'Error occured while trying to create candidates: {e}'
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)
