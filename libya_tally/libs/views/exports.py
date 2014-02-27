import csv
import os

from collections import defaultdict, OrderedDict

from django.core.files.base import File
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from tempfile import NamedTemporaryFile

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState


OUTPUT_PATH = 'results/candidate_votes.csv'
RESULTS_PATH = 'results/form_results.csv'
DUPLICATE_RESULTS_PATH = 'results/duplicate_results.csv'
SPECIAL_BALLOTS = None


def path_with_timestamp(path):
    if isinstance(path, basestring):
        tmp = path.split('.')
        time_str = timezone.now().strftime('%Y%m%d_%H-%M-%S')
        tmp.insert(len(tmp) - 1, time_str)

        return '.'.join(tmp)

    return path


def save_csv_file_and_symlink(csv_file, path):
    new_path = path_with_timestamp(path)
    default_storage.save(new_path, File(open(csv_file.name)))
    new_path = os.path.realpath(new_path)
    path = os.path.realpath(path)
    if os.path.exists(path):
        os.unlink(path)
    os.symlink(new_path, path)
    return path


def valid_ballots():
    return Ballot.objects.exclude(number=54)


def export_to_csv_response(queryset, headers, fields, filename='data.csv'):
    response = HttpResponse(content_type='text/csv')
    response['Content-Desposition'] = 'attachment; filename=%s' % filename

    w = csv.writer(response, csv.excel)
    w.writerow([smart_str(col) for col in headers])

    for obj in queryset:
        row = []
        for field in fields:
            row.append(smart_str(getattr(obj, field)))
        w.writerow(row)

    return response


def distinct_forms(ballot):
    forms = ResultForm.distinct_filter(ballot.resultform_set)

    if not forms:
        forms = ResultForm.distinct_for_component(ballot)

    return forms


def get_votes(candidate):
    """Return the active results for this candidate that are for archived
    result forms."""
    results = candidate.results.filter(
        entry_version=EntryVersion.FINAL,
        active=True, result_form__form_state=FormState.ARCHIVED).all()

    return [len(results), sum([r.votes for r in results])]


def build_result_and_recon_output(result_form):
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
                         output_to_file=True):
    center_to_votes = defaultdict(list)
    center_to_forms = defaultdict(list)
    ballots_to_candidates = {}

    for ballot in valid_ballots():
        ballots_to_candidates[ballot.number] = \
            ballot.candidates.all().order_by('order')

    csv_file = NamedTemporaryFile(delete=False, suffix='.csv')

    with csv_file as f:
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
            'number registrants'
        ]

        w = csv.DictWriter(f, header)
        w.writeheader()

        result_forms = ResultForm.objects\
            .select_related().filter(barcode__in=complete_barcodes)

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

                w.writerow({
                    k: v.encode('utf8') if isinstance(v, basestring)
                    else v for k, v in output.items()})

            # store votes for this forms center
            center = result_form.center
            center_to_votes[center.code].append(vote_list)
            center_to_forms[center.code].append(result_form)

    if output_to_file:
        save_csv_file_and_symlink(csv_file, RESULTS_PATH)
    if output_duplicates:
        return save_center_duplicates(center_to_votes, center_to_forms,
                                      output_to_file=output_to_file)
    return csv_file.name


def save_center_duplicates(center_to_votes, center_to_forms,
                           output_to_file=True):
    print '[INFO] Exporting vote duplicate records'

    csv_file = NamedTemporaryFile(delete=False, suffix='.csv')

    with csv_file as f:
        header = ['ballot', 'center', 'barcode', 'state', 'station', 'votes']
        w = csv.DictWriter(f, header)
        w.writeheader()

        for code, vote_lists in center_to_votes.items():
            votes_cast = sum([sum(l) for l in vote_lists]) > 0
            num_vote_lists = len(vote_lists)
            num_distinct_vote_lists = len(set(vote_lists))

            if votes_cast and num_distinct_vote_lists < num_vote_lists:
                print ('[WARNING] Matching votes for center %s, %s vote lists'
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

                        w.writerow({
                            k: v.encode('utf8') if isinstance(v, basestring)
                            else v for k, v in output.items()})
    if output_to_file:
        return save_csv_file_and_symlink(csv_file, DUPLICATE_RESULTS_PATH)

    return csv_file.name


def export_candidate_votes(output=None, save_barcodes=False,
                           output_duplicates=True, output_to_file=True):
    header = ['ballot number',
              'stations',
              'stations completed',
              'stations percent completed']

    max_candidates = 0
    for ballot in Ballot.objects.all():
        if ballot.candidates.count() > max_candidates:
            max_candidates = ballot.candidates.count()

    for i in xrange(1, max_candidates + 1):
        header.append('candidate %s name' % i)
        header.append('candidate %s votes' % i)

    complete_barcodes = []

    csv_file = NamedTemporaryFile(delete=False, suffix='.csv')

    with csv_file as f:
        w = csv.DictWriter(f, header)
        w.writeheader()

        for ballot in valid_ballots():
            general_ballot = ballot
            forms = distinct_forms(ballot)
            final_forms = forms.filter(form_state=FormState.ARCHIVED)

            if not SPECIAL_BALLOTS or ballot.number in SPECIAL_BALLOTS:
                complete_barcodes.extend([r.barcode for r in final_forms])

            num_stations = forms.count()
            num_stations_completed = final_forms.count()

            percent_complete = round(
                100 * num_stations_completed / num_stations, 3)

            output = OrderedDict({
                'ballot number': ballot.number,
                'stations': num_stations,
                'stations completed': num_stations_completed,
                'stations percent completed': percent_complete})

            candidates_to_votes = {}
            num_results_ary = []

            for candidate in ballot.candidates.all():
                num_results, votes = get_votes(candidate)
                candidates_to_votes[candidate.full_name] = votes
                num_results_ary.append(num_results)

            assert len(set(num_results_ary)) <= 1

            for num_results in num_results_ary:
                if num_stations_completed != num_results:
                    print ('[WARNING] Number stations complete (%s) not '
                           'equal to num_results (%s) for ballot %s (general'
                           ' ballot %s)' % (
                               num_stations_completed, num_results,
                               ballot.number, general_ballot.number))
                    output['stations completed'] = num_results

            candidates_to_votes = OrderedDict((sorted(
                candidates_to_votes.items(), key=lambda t: t[1],
                reverse=True)))

            for i, item in enumerate(candidates_to_votes.items()):
                candidate, votes = item

                output['candidate %s name' % (i + 1)] = candidate
                output['candidate %s votes' % (i + 1)] = votes

            w.writerow({k: v.encode('utf8') if isinstance(v, basestring)
                        else v for k, v in output.items()})

    if output_to_file:
        save_csv_file_and_symlink(csv_file, OUTPUT_PATH)
    if save_barcodes:
        return save_barcode_results(complete_barcodes,
                                    output_duplicates=output_duplicates,
                                    output_to_file=output_to_file)
    return csv_file.name


def get_result_export_response(report):
    filename = 'not_found.csv'
    path = None
    if report == 'formresults':
        filename = 'form_results.csv'
        path = export_candidate_votes(save_barcodes=True,
                                      output_duplicates=False,
                                      output_to_file=False)
    elif report == 'candidates':
        filename = 'candidates_votes.csv'
        path = export_candidate_votes(output_to_file=False)
    elif report == 'duplicates':
        filename = 'duplicates.csv'
        path = export_candidate_votes(save_barcodes=True,
                                      output_duplicates=True,
                                      output_to_file=False)
    response = HttpResponse(content_type='text/csv')
    response['Content-Desposition'] = 'attachment; filename=%s' % filename

    if path:
        with open(path, 'rb') as f:
            response.write(f.read())
        os.remove(path)
    else:
        response.write(_(u"Report not found."))
        response.status_code = 404
    return response
