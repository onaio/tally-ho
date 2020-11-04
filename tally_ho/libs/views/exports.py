from collections import defaultdict, OrderedDict
import csv
import os
from tempfile import NamedTemporaryFile

from django.core.files.base import File
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState


OUTPUT_PATH = 'results/all_candidate_votes_%s.csv'
ACTIVE_OUTPUT_PATH = 'results/active_candidate_votes_%s.csv'
RESULTS_PATH = 'results/form_results_%s.csv'
DUPLICATE_RESULTS_PATH = 'results/duplicate_results_%s.csv'
SPECIAL_BALLOTS = None


def path_with_timestamp(path):
    if isinstance(path, str):
        tmp = path.split('.')
        time_str = timezone.now().strftime('%Y%m%d_%H-%M-%S')
        tmp.insert(len(tmp) - 1, time_str)

        return '.'.join(tmp)

    return path


def save_csv_file_and_symlink(csv_file, path):
    new_path = path_with_timestamp(path)
    file_path =\
        default_storage.save(new_path, File(open(csv_file.name, mode='r')))
    new_path = default_storage.path(file_path)

    try:
        os.symlink(new_path, path)
    except FileExistsError:
        os.unlink(os.path.abspath(path))
        os.symlink(new_path, path)
    return path


def write_utf8(w, output):
    """Encode strings in the dict output as utf8 and write to w.

    :param w: A stream to write a row to.
    :param output: A dict to encode as utf8.
    """
    w.writerow({k: v for k, v in output.items()})


def valid_ballots(tally_id=None):
    return Ballot.objects.filter(tally__id=tally_id)


def distinct_forms(ballot, tally_id):
    """Return the distinct forms for a ballot based on its type.

    If there are no forms for a ballot assume that it is a component ballot and
    return forms for the associated general ballots.

    :param ballot: The ballot to return distinct forms for.

    :returns: The list of result forms.
    """
    forms = ResultForm.distinct_filter(ballot.resultform_set, tally_id)

    if not forms:
        forms = ResultForm.distinct_for_component(ballot, tally_id)

    return forms


def build_result_and_recon_output(result_form):
    """Build dict of data from a result form and add reconciliation information
    if it has a reconciliation form.

    :param result_form: The result form to build data for.

    :returns: A dict of information about this result form.
    """
    output = {
        'ballot': result_form.ballot.number,
        'center': result_form.center.code,
        'station': result_form.station_number,
        'gender': result_form.gender_name,
        'barcode': result_form.barcode,
        'race type': result_form.ballot_race_type_name,
        'voting district': result_form.ballot.sub_constituency.code,
        'number registrants': result_form.station.registrants
    }

    recon = result_form.reconciliationform

    if recon:
        output.update({
            'invalid ballots': recon.number_invalid_votes,
            'unstamped ballots': recon.number_unstamped_ballots,
            'cancelled ballots': recon.number_cancelled_ballots,
            'spoilt ballots': recon.number_spoiled_ballots,
            'unused ballots': recon.number_unused_ballots,
            'number of signatures': recon.number_signatures_in_vr,
            'received ballots papers': recon.number_ballots_received,
            'valid votes': recon.number_valid_votes,
        })

    return output


def save_barcode_results(complete_barcodes, output_duplicates=False,
                         output_to_file=True, tally_id=None):
    """Save a list of results for all candidates in all result forms.

    :param complete_barcodes: The set of barcodes for result forms.
    :param output_duplicates: Generate list of duplicates after, default False.
    :param output_to_file: Output results as file, default True.

    :returns: The name of the temporary file that results were saved to.
    """
    center_to_votes = defaultdict(list)
    center_to_forms = defaultdict(list)
    ballots_to_candidates = {}

    for ballot in valid_ballots(tally_id):
        ballots_to_candidates[ballot.number] = \
            ballot.candidates.all().order_by('order')

    csv_file = NamedTemporaryFile(delete=False, suffix='.csv')

    with open(csv_file.name, 'w') as f:
        header = [
            'ballot',
            'race number',
            'center',
            'station',
            'gender',
            'barcode',
            'race type',
            'voting district',
            'order',
            'name', 'votes',
            'invalid ballots',
            'unstamped ballots',
            'cancelled ballots',
            'spoilt ballots',
            'unused ballots',
            'number of signatures',
            'received ballots papers',
            'valid votes',
            'number registrants',
            'candidate status',
        ]

        w = csv.DictWriter(f, header)
        w.writeheader()

        result_forms = ResultForm.objects.select_related().filter(
            barcode__in=complete_barcodes, tally__id=tally_id)

        for result_form in result_forms:
            # build list of votes for this barcode
            vote_list = ()
            output = build_result_and_recon_output(result_form)

            for candidate in result_form.candidates:
                votes = candidate.num_votes(result_form)
                vote_list += (votes,)

                output['order'] = candidate.order
                output['name'] = candidate.full_name
                output['votes'] = votes
                output['race number'] = candidate.ballot.number
                if candidate.active:
                    output['candidate status'] = 'enabled'
                else:
                    output['candidate status'] = 'disabled'

                write_utf8(w, output)

            # store votes for this forms center
            center = result_form.center
            center_to_votes[center.code].append(vote_list)
            center_to_forms[center.code].append(result_form)

    if output_to_file:
        save_csv_file_and_symlink(csv_file, RESULTS_PATH % tally_id)

    if output_duplicates:
        return save_center_duplicates(center_to_votes,
                                      center_to_forms,
                                      output_to_file=output_to_file,
                                      tally_id=tally_id)
    return csv_file.name


def save_center_duplicates(center_to_votes, center_to_forms,
                           output_to_file=True,
                           tally_id=None):
    """Output list of forms with duplicates votes in the same center.

    :param center_to_votes: A dict mapping centers to a list of votes for that
        center.
    :param center_to_forms: A dict mapping centers to the result forms for that
        center
    :param output_to_file: Output results to a file, default True.

    :returns: The name of the temporary file that results have been output to.
    """
    print('[INFO] Exporting vote duplicate records')

    csv_file = NamedTemporaryFile(delete=False, suffix='.csv')

    with open(csv_file.name, 'w') as f:
        header = ['ballot', 'center', 'barcode', 'state', 'station', 'votes']
        w = csv.DictWriter(f, header)
        w.writeheader()

        for code, vote_lists in center_to_votes.items():
            votes_cast = sum([sum(vote) for vote in vote_lists]) > 0
            num_vote_lists = len(vote_lists)
            num_distinct_vote_lists = len(set(vote_lists))

            if votes_cast and num_distinct_vote_lists < num_vote_lists:
                print('[WARNING] Matching votes for center %s, %s vote lists'
                      % (code, num_vote_lists))

                for i, form in enumerate(center_to_forms[code]):
                    vote_list = vote_lists[i]
                    votes_cast = sum(vote_list) > 0
                    other_vote_lists = vote_lists[:i] + vote_lists[i + 1:]

                    if votes_cast and vote_list in other_vote_lists:
                        output = {
                            'ballot': form.ballot.number,
                            'center': code,
                            'barcode': form.barcode,
                            'state': form.form_state_name,
                            'station': form.station_number,
                            'votes': vote_list
                        }

                        write_utf8(w, output)

    if output_to_file:
        return save_csv_file_and_symlink(csv_file,
                                         DUPLICATE_RESULTS_PATH % tally_id)

    return csv_file.name


def export_candidate_votes(save_barcodes=False,
                           output_duplicates=True,
                           output_to_file=True,
                           show_disabled_candidates=True,
                           tally_id=None):
    """Export a spreadsheet of the candidates their votes for each race.

    :param save_barcodes: Generate barcode result file, default False.
    :param output_duplicates: Generate duplicates file, default True.
    :param output_to_file: Output to file, default True.

    :returns: The name of the temporary file that results have been output to.
    """
    header = ['ballot number',
              'stations',
              'stations completed',
              'stations percent completed']

    max_candidates = 0

    for ballot in Ballot.objects.filter(tally__id=tally_id):
        if not show_disabled_candidates:
            ballot_number = ballot.candidates.filter(active=True).count()
        else:
            ballot_number = ballot.candidates.count()

        if ballot_number > max_candidates:
            max_candidates = ballot_number

    for i in range(1, max_candidates + 1):
        header.append('candidate %s name' % i)
        header.append('candidate %s votes' % i)
        header.append('candidate %s votes included quarantine' % i)

    complete_barcodes = []

    csv_file = NamedTemporaryFile(delete=False, suffix='.csv')
    with open(csv_file.name, 'w') as f:
        w = csv.DictWriter(f, header)
        w.writeheader()

        for ballot in valid_ballots(tally_id):
            general_ballot = ballot
            forms = distinct_forms(ballot, tally_id)
            final_forms = ResultForm.forms_in_state(
                FormState.ARCHIVED, pks=[r.pk for r in forms])

            if not SPECIAL_BALLOTS or ballot.number in SPECIAL_BALLOTS:
                complete_barcodes.extend([r.barcode for r in final_forms])

            num_stations = forms.count()
            num_stations_completed = final_forms.count()

            percent_complete = round(
                100 * num_stations_completed / num_stations, 3) if \
                num_stations else 0

            output = OrderedDict({
                'ballot number': ballot.number,
                'stations': num_stations,
                'stations completed': num_stations_completed,
                'stations percent completed': percent_complete})

            candidates_to_votes = {}
            num_results_ary = []

            candidates = ballot.candidates.all()
            if not show_disabled_candidates:
                candidates = candidates.filter(active=True)

            for candidate in candidates:
                num_results, votes = candidate.num_votes()
                all_votes = candidate.num_all_votes
                candidates_to_votes[candidate.full_name] = [votes, all_votes]
                num_results_ary.append(num_results)

            assert len(set(num_results_ary)) <= 1

            for num_results in num_results_ary:
                if num_stations_completed != num_results:
                    print('[WARNING] Number stations complete (%s) not '
                          'equal to num_results (%s) for ballot %s (general'
                          ' ballot %s)' % (
                              num_stations_completed, num_results,
                              ballot.number, general_ballot.number))
                    output['stations completed'] = num_results

            candidates_to_votes = OrderedDict((sorted(
                candidates_to_votes.items(), key=lambda t: t[1][0],
                reverse=True)))

            # Checks changes in candidates positions
            check_position_changes(candidates_to_votes)

            for i, item in enumerate(candidates_to_votes.items()):
                candidate, votes = item

                output['candidate %s name' % (i + 1)] = candidate
                output['candidate %s votes' % (i + 1)] = votes[0]
                output['candidate %s votes included quarantine' %
                       (i + 1)] = votes[1]

            write_utf8(w, output)

    if output_to_file:
        if show_disabled_candidates:
            save_csv_file_and_symlink(csv_file, OUTPUT_PATH % tally_id)
        else:
            save_csv_file_and_symlink(csv_file, ACTIVE_OUTPUT_PATH % tally_id)

    if save_barcodes:
        return save_barcode_results(complete_barcodes,
                                    output_duplicates=output_duplicates,
                                    output_to_file=output_to_file,
                                    tally_id=tally_id)
    return csv_file.name


def check_position_changes(candidates_votes):
    """Order candidates by valid votes and all votes included quarantine
    """
    sort_valid_votes = OrderedDict((sorted(
        candidates_votes.items(), key=lambda t: t[1][0],
        reverse=True)))
    sort_all_votes = OrderedDict((sorted(
        candidates_votes.items(), key=lambda t: t[1][1],
        reverse=True)))

    # Get first five candidates
    valid_votes = dict(enumerate(list(sort_valid_votes.keys())[0:5]))
    all_votes = dict(enumerate(list(sort_all_votes.keys())[0:5]))

    # If they are not de same, warn the super-admin
    if valid_votes != all_votes:
        # TODO: how show be warn super admin?
        pass


def get_result_export_response(report, tally_id):
    """Choose the appropriate file to returns as an HTTP Response.

    :param report: The type of report to return.

    :returns: An HTTP response.
    """
    filename = 'not_found.csv'
    path = None
    show_disabled = True

    if report == 'formresults':
        filename = os.path.join('results', 'form_results_%d.csv' % tally_id)
    elif report == 'all-candidates':
        filename = os.path.join('results',
                                'all_candidate_votes_%d.csv' % tally_id)
    elif report == 'active-candidates':
        filename = os.path.join('results',
                                'active_candidate_votes_%d.csv' % tally_id)
        show_disabled = False
    elif report == 'duplicates':
        filename = os.path.join('results',
                                'duplicate_results_%d.csv' % tally_id)

    response = HttpResponse(content_type='text/csv')

    try:
        # FIXME: if file it's been already generated,
        # does not generate new one. correct??
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        export_candidate_votes(save_barcodes=True,
                               output_duplicates=True,
                               show_disabled_candidates=show_disabled,
                               tally_id=tally_id)

        path = os.readlink(filename)
        filename = os.path.basename(path)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        response['Content-Type'] = 'text/csv; charset=utf-8'

        if path:
            with open(path, 'rb') as f:
                response.write(f.read())
        else:
            raise Exception(_(u"File Not found!"))

    except Exception:
        response.write(_(u"Report not found."))
        response.status_code = 404

    return response
