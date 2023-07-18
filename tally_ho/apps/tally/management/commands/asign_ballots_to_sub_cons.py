import duckdb
import logging
from django.conf import settings
from tally_ho.apps.tally.management.commands.utils import (
    check_for_missing_columns
)
from tally_ho.apps.tally.models.ballot import Ballot

from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.utils.numbers import parse_int
from tally_ho.libs.utils.query_set_helpers import BulkUpdateManyToManyManager
from tally_ho.celeryapp import app
from tally_ho.libs.utils.memcache import MemCache

logger = logging.getLogger(__name__)

def set_sub_constituencies_ballots_from_sub_con_ballots_file_data(
        duckdb_sub_con_ballots_data=None,
        tally=None,
        command=None,
        step_name=None,
        step_number=1,
):
    """Set sub constituencies ballots from sub constituencies ballots file data
        inside duckdb.

    :param duckdb_sub_con_ballots_data: sub cons ballots data in duckdb format.
    :param tally: tally queryset.
    :param step_name: step name.
    :param step_number: step number.
    :param command: stdout command.
    :returns: None."""
    try:
        instances_count_memcache_key =\
            f"{tally.id}_{step_name}_{step_number}"
        # reset instances count in memcache if exists already
        client = MemCache()
        client.delete(instances_count_memcache_key)
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
            BulkUpdateManyToManyManager(
                instances_count=len(sub_con_code_data),
                cache_instances_count=True,
                cache_key=instances_count_memcache_key,
                memcache_client=client)

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
        raise Exception(msg)

@app.task()
def async_asign_ballots_to_sub_cons_from_ballots_file(
        tally_id,
        csv_file_path,
        command=None,
        **kwargs):
    """Import sub constituencies ballots from a sub constituencies ballots
    csv file.

    :param tally_id: tally id.
    :param csv_file_path: sub constituencies csv file path.
    :param command: stdout command.
    :returns: Sub Constituencies count."""
    try:
        tally = Tally.objects.get(id=tally_id)
        file_path =\
            csv_file_path
        duckdb_sub_con_ballots_data =\
            duckdb.from_csv_auto(file_path, header=True)
        sub_con_ballots_col_names =\
            getattr(settings,
                    'SUB_CONSTITUENCY_BALLOTS_COLUMN_NAMES')
        check_for_missing_columns(
            sub_con_ballots_col_names,
            duckdb_sub_con_ballots_data.columns,
            'sub constituency ballots'
        )
        set_sub_constituencies_ballots_from_sub_con_ballots_file_data(
            duckdb_sub_con_ballots_data=duckdb_sub_con_ballots_data,
            tally=tally,
            command=command,
            step_name=kwargs.get('step_name'),
            step_number=kwargs.get('step_number'),
        )

        return len(duckdb_sub_con_ballots_data.fetchall())
    except Exception as e:
        msg =\
            'Error occured while trying to create sub cons and cons: %s' % e
        if command:
            command.stdout.write(command.style.WARNING(msg))
        if logger:
            logger.warning(msg)
        raise Exception(msg)
