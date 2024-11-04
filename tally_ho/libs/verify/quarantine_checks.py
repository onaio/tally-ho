from django.conf import settings

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck


def create_quarantine_checks(quarantine_data=None):
    quarantine_data =\
        quarantine_data if quarantine_data is not None\
                        else getattr(settings, 'QUARANTINE_DATA')
    for quarantine_check in quarantine_data:
        try:
            QuarantineCheck.objects.get(method=quarantine_check['method'])
        except QuarantineCheck.DoesNotExist:
            QuarantineCheck.objects.create(**quarantine_check)

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def get_total_candidates_votes(result_form):
    """Calculate total candidates votes for the result form

    If the result form is a component ballot, get the candidates votes
    from the general ballot component and combine them with the
    candidates votes from the ballot.

    Sum ballot candidates votes and ballot component votes to get total votes.

    :param result_form: The result form to get candidates.
    :returns: A Int of total candidates votes.
    """

    # vote_list = ()

    # for candidate in result_form.candidates:
    #     votes = candidate.num_votes(result_form, result_form.form_state)
    #     vote_list += (votes,)

    # return sum(vote_list)


def quarantine_checks():
    """Return tuples of (QuarantineCheck, validation_function)."""
    all_methods = {
                   'pass_registrants_trigger':
                   pass_registrants_trigger,
                   'pass_voter_cards_trigger':
                   pass_voter_cards_trigger,
                   'pass_ballot_papers_trigger':
                   pass_ballot_papers_trigger,
                   'pass_ballot_inside_box_trigger':
                   pass_ballot_inside_box_trigger,
                   'pass_candidates_votes_trigger':
                   pass_candidates_votes_trigger,
                }
    methods = []

    quarantine_checks_methods =\
        QuarantineCheck.objects.filter(
            active=True).values_list('method', flat=True).order_by('pk')

    for method_name in quarantine_checks_methods:
        methods.append(all_methods[method_name])

    checks =\
        QuarantineCheck.objects.filter(active=True).order_by('pk')

    return zip(methods, checks)

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_overvote(result_form):
    """Check to guard against overvoting.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    If the `station` for this `result_form` has an empty `registrants` field
    this will always return True.

    Fails if the number of ballots reported to be used in a station exceeds
    the number of potential voters minus the number of registrants plus N
    persons to accomodate staff and security.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    pass
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # registrants = result_form.station.registrants if result_form.station\
    #     else None

    # if registrants is None:
    #     return True

    # qc = QuarantineCheck.objects.get(method='pass_overvote')
    # max_number_ballots = (qc.percentage / 100) * registrants + qc.value

    # return recon_form.number_ballots_used <= max_number_ballots

def pass_registrants_trigger(result_form):
    """Summation of recon fields number_cancelled_ballots and
    number_ballots_inside_box must be less than or equal to the number of
    registered voters at the station.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    If the `station` for this `result_form` has an empty `registrants` field
    this will always return True.

    Fails if the summation of recon fields number_cancelled_ballots and
    number_ballots_inside_box exceeds the number of potential voters minus
    the number of registrants plus N persons to accomodate staff and security.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    registrants = result_form.station.registrants if result_form.station\
        else None

    if registrants is None:
        return True

    qc = QuarantineCheck.objects.get(method='pass_registrants_trigger')
    potential_voters_num = registrants + qc.value

    return recon_form.total_of_cancelled_ballots_and_ballots_inside_box <=\
        potential_voters_num

def pass_voter_cards_trigger(result_form):
    """Summation of recon fields number_cancelled_ballots and
    number_ballots_inside_box must be equal to
    number_of_voter_cards_in_the_ballot_box

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    return recon_form.total_of_cancelled_ballots_and_ballots_inside_box ==\
        recon_form.number_of_voter_cards_in_the_ballot_box

def pass_ballot_papers_trigger(result_form):
    """The total number of ballots received by the polling station must be
    equal to the total number of ballots found inside and outside the
    ballot box.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    return recon_form.number_ballots_received ==\
        recon_form.number_ballots_inside_and_outside_box

def pass_ballot_inside_box_trigger(result_form):
    """The total number of ballots found inside the ballot box must be
    equal to the summation of the number of unstamped ballots and the
    number of invalid votes (including the blanks) and
    the number of valid votes

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    return (
        recon_form.number_unstamped_ballots +
        recon_form.number_invalid_votes +
        recon_form.number_valid_votes
    ) ==\
        recon_form.number_ballots_inside_box

def pass_candidates_votes_trigger(result_form):
    """The total number of the sorted and counted ballots must be
    equal to the total votes distributed among the candidates.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    return result_form.num_votes == recon_form.number_sorted_and_counted

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_tampering(result_form):
    """Guard against errors and tampering with the form.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    Fails if the sum of the results section of the form does not equal the
    number of ballots expected based on the calculation of the key fields from
    the reconciliation form with a N% tolerance.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # num_votes = result_form.num_votes
    # number_ballots_expected = recon_form.number_ballots_expected
    # diff = abs(num_votes - number_ballots_expected)
    # TODO Check if 'qc' variable must be QuarantineCheck object with method
    # # 'pass_tampering' or not
    # qc = QuarantineCheck.objects.get(method='pass_tampering')
    # scaled_tolerance = (qc.value / 100) * (
    #     num_votes + number_ballots_expected) / 2

    # return diff <= scaled_tolerance

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_ballots_number_validation(result_form):
    """Validate that the total number of received ballots equals the
    total of the ballots inside the box plus ballots outside the box.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # ballots_inside_and_outside_the_box = (
    #     recon_form.number_ballots_inside_the_box +
    #     recon_form.number_ballots_outside_the_box)
    # number_ballots_received = recon_form.number_ballots_received
    # diff = abs(number_ballots_received - ballots_inside_and_outside_the_box)
    # qc = QuarantineCheck.objects.get(method='pass_ballots_number_validation')
    # scaled_tolerance = (qc.value / 100) * (
    #     number_ballots_received + ballots_inside_and_outside_the_box) / 2

    # return diff <= scaled_tolerance

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_signatures_validation(result_form):
    """Validate that the total number of signatures on the voter list for
    the voters who voted equals the number of ballots found in the ballot
    box after polling plus cancelled ballots.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # cancelled_ballots_and_ballots_inside_the_box = (
    #     recon_form.number_ballots_inside_the_box +
    #     recon_form.number_cancelled_ballots)
    # number_of_voter_cards_in_the_ballot_box =\
    #     recon_form.number_of_voter_cards_in_the_ballot_box
    # diff =\
    #     abs(number_of_voter_cards_in_the_ballot_box -
    #         cancelled_ballots_and_ballots_inside_the_box)
    # qc = QuarantineCheck.objects.get(method='pass_signatures_validation')
    # scaled_tolerance =\
    #     (qc.value / 100) * (number_of_voter_cards_in_the_ballot_box +
    #                         cancelled_ballots_and_ballots_inside_the_box) / 2

    # return diff <= scaled_tolerance

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_ballots_inside_box_validation(result_form):
    """The total number of ballot papers inside the ballot box will be
    compared against the total of valid, invalid, and unstamped ballots.

    Fails if the value of number_ballots_inside_box from the recon form
    does not equal the value of the recon property
    number_ballots_inside_the_box with an N% tolerance.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # # Number of ballots value entered by data entry clerk on the recon form
    # number_ballots_inside_box = recon_form.number_ballots_inside_box

    # # The total of valid, invalid, and unstamped ballots
    # number_ballots_inside_the_box = recon_form.number_ballots_inside_the_box
    # diff =\
    #     abs(number_ballots_inside_box -
    #         number_ballots_inside_the_box)
    # qc = QuarantineCheck.objects.get(
    #     method='pass_ballots_inside_box_validation')
    # scaled_tolerance =\
    #     (qc.value / 100) * (number_ballots_inside_box +
    #                         number_ballots_inside_the_box) / 2

    # return diff <= scaled_tolerance

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_sum_of_candidates_votes_validation(result_form):
    """The total votes for candidates should equal the valid ballots:
    after sorting the ballots inside the ballot box as valid and invalid,
    and unstamped, the number of valid ballots should equal the
    sum of all candidates votes.

    Fails if the value of number_valid_votes from the recon form
    does not equal the sum of all candidates votes from the result form
    with an N% tolerance.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # total_candidates_votes = get_total_candidates_votes(result_form)
    # number_valid_votes = recon_form.number_valid_votes

    # diff = total_candidates_votes - number_valid_votes

    # return diff > 0

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_invalid_ballots_percentage_validation(result_form):
    """Validate the percentage of invalid ballots.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    Fails if the percentage of invalid ballots is greater than the this
    trigger percentage value.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # qc = QuarantineCheck.objects.get(
    #     method='pass_invalid_ballots_percentage_validation')
    # invalid_ballots_percentage =\
    #     100 * (recon_form.number_invalid_votes /
    #            recon_form.number_ballots_inside_the_box)
    # allowed_invalid_ballots_percentage = qc.percentage

    # return invalid_ballots_percentage <= allowed_invalid_ballots_percentage

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_turnout_percentage_validation(result_form):
    """Validate the turnout percentage.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    If the `station` for this `result_form` has an empty `registrants` field
    this will always return True.

    Fails if the turnout percentage is greater than the this trigger percentage
    value.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # registrants = result_form.station.registrants if result_form.station\
    #     else None

    # if registrants is None:
    #     return True

    # qc = QuarantineCheck.objects.get(
    #     method='pass_turnout_percentage_validation')

    # turnout_percentage = 100 * (recon_form.number_ballots_used / registrants)
    # allowed_turnout_percentage = qc.percentage

    # return turnout_percentage <= allowed_turnout_percentage

# Disabled: Awaiting client feedback for final removal.
# This function is temporarily inactive; it will be removed if the client
# confirms it is no longer required.
def pass_percentage_of_votes_per_candidate_validation(result_form):
    """Validate that the percentage of votes per candidate of the total
    valid votes does not exceed a certain threshold.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    Fails if the percentage of votes for a particular candidate of the total
    valid votes is greater than the this trigger percentage value.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    # recon_form = result_form.reconciliationform

    # if not recon_form:
    #     return True

    # qc = QuarantineCheck.objects.get(
    #     method='pass_percentage_of_votes_per_candidate_validation')
    # allowed_candidate_votes_percentage = qc.percentage
    # total_candidates_votes = get_total_candidates_votes(result_form)

    # for candidate in result_form.candidates:
    #     candidate_votes =\
    #         candidate.num_votes(result_form=result_form,
    #                             form_state=FormState.QUALITY_CONTROL)
    #     candidate_votes_percentage =\
    #         100 * (candidate_votes/total_candidates_votes)

    #     if candidate_votes_percentage > allowed_candidate_votes_percentage:
    #         return False

    # return True


def check_quarantine(result_form, user):
    """Run quarantine checks.  Create an audit with links to the failed
    quarantine checks if any fail.

    :param result_form: The result form to run quarantine checks on.
    :param user: The user to associate with an audit if any checks fail.
    """
    audit = None

    if not result_form.skip_quarantine_checks:
        for passed_check, check in quarantine_checks():
            if not passed_check(result_form):
                if not audit:
                    audit = Audit.objects.create(
                        user=user.userprofile,
                        result_form=result_form)

                audit.quarantine_checks.add(check)

    if audit:
        result_form.audited_count += 1
        result_form.save()
