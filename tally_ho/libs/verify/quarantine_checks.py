from django.conf import settings

from django.db.models.functions import Coalesce
from django.db.models import (
    Sum, F, IntegerField, ExpressionWrapper, Case, When, Q, Value as V)

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState


def create_quarantine_checks():
    for quarantine_check in getattr(settings, 'QUARANTINE_DATA'):
        QuarantineCheck.objects.get_or_create(
            name=quarantine_check['name'],
            method=quarantine_check['method'],
            active=quarantine_check['active'],
            value=quarantine_check['value'],
            percentage=quarantine_check['percentage']
        )


def get_total_candidates_votes(result_form):
    """Calculate total candidates votes for the result form

    If the result form is a component ballot, get the candidates votes
    from the general ballot component and combine them with the
    candidates votes from the ballot.

    Sum ballot candidates votes and ballot component votes to get total votes.

    :param result_form: The result form to get candidates.
    :returns: A Int of total candidates votes.
    """
    ids = [candidate.id for candidate in result_form.candidates]

    filter_ballot_component_candidates_by_id =\
        Q(ballot__sc_general__ballot_component__candidates__id__in=ids)
    ballot_component_candidates_votes_field =\
        'ballot__sc_general__ballot_component__candidates__results__votes'
    ballot_component_votes =\
        Coalesce(
            Sum(
                Case(
                    When(
                        ballot__sc_general__ballot_component__isnull=False
                        and
                        filter_ballot_component_candidates_by_id,
                        then=ballot_component_candidates_votes_field)
                )
            ),
            V(0)
        )

    total_votes =\
        ResultForm.objects.filter(pk=result_form.id)\
        .annotate(
            ballot_candidates_votes=Coalesce(
                Sum('ballot__candidates__results__votes',
                    filter=Q(ballot__candidates__id__in=ids)),
                V(0)))\
        .annotate(
            ballot_component_candidates_votes=ballot_component_votes)\
        .annotate(
            total_votes=ExpressionWrapper(
                F('ballot_candidates_votes') +
                F('ballot_component_candidates_votes'),
                output_field=IntegerField()
            )
        ).values('total_votes')[0]['total_votes']

    return total_votes


def quarantine_checks():
    """Return tuples of (QuarantineCheck, validation_function)."""
    all_methods = {'pass_overvote':
                   pass_overvote,
                   'pass_tampering':
                   pass_tampering,
                   'pass_ballots_number_validation':
                   pass_ballots_number_validation,
                   'pass_signatures_validation':
                   pass_signatures_validation,
                   'pass_ballots_inside_box_validation':
                   pass_ballots_inside_box_validation,
                   'pass_sum_of_candidates_votes_validation':
                   pass_sum_of_candidates_votes_validation,
                   'pass_invalid_ballots_percentage_validation':
                   pass_invalid_ballots_percentage_validation,
                   'pass_turnout_percentage_validation':
                   pass_turnout_percentage_validation,
                   'pass_percentage_of_votes_per_candidate_validation':
                   pass_percentage_of_votes_per_candidate_validation,
                   'pass_percentage_of_blank_ballots_trigger':
                   pass_percentage_of_blank_ballots_trigger}
    methods = []

    quarantine_checks_methods =\
        QuarantineCheck.objects.filter(
            active=True).values_list('method', flat=True).order_by('pk')

    for method_name in quarantine_checks_methods:
        methods.append(all_methods[method_name])

    checks =\
        QuarantineCheck.objects.filter(active=True).order_by('pk')

    return zip(methods, checks)


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
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    registrants = result_form.station.registrants if result_form.station\
        else None

    if registrants is None:
        return True

    qc = QuarantineCheck.objects.get(method='pass_overvote')
    max_number_ballots = (qc.percentage / 100) * registrants + qc.value

    return recon_form.number_ballots_used <= max_number_ballots


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
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    num_votes = result_form.num_votes
    number_ballots_expected = recon_form.number_ballots_expected
    diff = abs(num_votes - number_ballots_expected)
    # TODO Check if 'qc' variable must be QuarantineCheck object with method
    # 'pass_tampering' or not
    qc = QuarantineCheck.objects.get(method='pass_tampering')
    scaled_tolerance = (qc.value / 100) * (
        num_votes + number_ballots_expected) / 2

    return diff <= scaled_tolerance


def pass_ballots_number_validation(result_form):
    """Validate that the total number of received ballots equals the
    total of the ballots inside the box plus ballots outside the box.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    ballots_inside_and_outside_the_box = (
        recon_form.number_ballots_inside_the_box +
        recon_form.number_ballots_outside_the_box)
    number_ballots_received = recon_form.number_ballots_received
    diff = abs(number_ballots_received - ballots_inside_and_outside_the_box)
    qc = QuarantineCheck.objects.get(method='pass_ballots_number_validation')
    scaled_tolerance = (qc.value / 100) * (
        number_ballots_received + ballots_inside_and_outside_the_box) / 2

    return diff <= scaled_tolerance


def pass_signatures_validation(result_form):
    """Validate that the total number of signatures on the voter list for
    the voters who voted equals the number of ballots found in the ballot
    box after polling plus cancelled ballots.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    cancelled_ballots_and_ballots_inside_the_box = (
        recon_form.number_ballots_inside_the_box +
        recon_form.number_cancelled_ballots)
    number_signatures_in_vr = recon_form.number_signatures_in_vr
    diff =\
        abs(number_signatures_in_vr -
            cancelled_ballots_and_ballots_inside_the_box)
    qc = QuarantineCheck.objects.get(method='pass_signatures_validation')
    scaled_tolerance =\
        (qc.value / 100) * (number_signatures_in_vr +
                            cancelled_ballots_and_ballots_inside_the_box) / 2

    return diff <= scaled_tolerance


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
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    # Number of ballots value entered by data entry clerk on the recon form
    number_ballots_inside_box = recon_form.number_ballots_inside_box

    # The total of valid, invalid, and unstamped ballots
    number_ballots_inside_the_box = recon_form.number_ballots_inside_the_box
    diff =\
        abs(number_ballots_inside_box -
            number_ballots_inside_the_box)
    qc = QuarantineCheck.objects.get(
        method='pass_ballots_inside_box_validation')
    scaled_tolerance =\
        (qc.value / 100) * (number_ballots_inside_box +
                            number_ballots_inside_the_box) / 2

    return diff <= scaled_tolerance


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
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    total_candidates_votes = get_total_candidates_votes(result_form)
    number_valid_votes = recon_form.number_valid_votes
    diff = abs(total_candidates_votes - number_valid_votes)

    qc = QuarantineCheck.objects.get(
        method='pass_sum_of_candidates_votes_validation')
    scaled_tolerance =\
        (qc.value / 100) * (total_candidates_votes + number_valid_votes) / 2

    return diff <= scaled_tolerance


def pass_invalid_ballots_percentage_validation(result_form):
    """Validate the percentage of invalid ballots.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    Fails if the percentage of invalid ballots is greater than the this
    trigger percentage value.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    qc = QuarantineCheck.objects.get(
        method='pass_invalid_ballots_percentage_validation')
    invalid_ballots_percantage =\
        (recon_form.number_invalid_votes /
         recon_form.number_ballots_inside_the_box) * 100
    allowed_invalid_ballots_percantage = qc.percentage

    return invalid_ballots_percantage <= allowed_invalid_ballots_percantage


def pass_percentage_of_blank_ballots_trigger(result_form):
    """Validate the percentage of blank ballots.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    Fails if the percentage of blank ballots is greater than the this
    trigger percentage value.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    qc = QuarantineCheck.objects.get(
        method='pass_percentage_of_blank_ballots_trigger')
    blank_ballots_percantage =\
        100 * (recon_form.number_blank_ballots /
               recon_form.number_ballots_inside_the_box)
    allowed_blank_ballots_percantage = qc.percentage

    return blank_ballots_percantage <= allowed_blank_ballots_percantage


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
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    registrants = result_form.station.registrants if result_form.station\
        else None

    if registrants is None:
        return True

    qc = QuarantineCheck.objects.get(
        method='pass_turnout_percentage_validation')

    turnout_percantage =\
        (recon_form.number_ballots_used / registrants) * 100
    allowed_turnout_percantage = qc.percentage

    return turnout_percantage <= allowed_turnout_percantage


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
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    qc = QuarantineCheck.objects.get(
        method='pass_percentage_of_votes_per_candidate_validation')
    allowed_candidate_votes_percentage = qc.percentage
    total_candidates_votes = get_total_candidates_votes(result_form)

    for candidate in result_form.candidates:
        candidate_votes =\
            candidate.num_votes(result_form=result_form,
                                form_state=FormState.QUALITY_CONTROL)
        candidate_votes_percentage =\
            (candidate_votes/total_candidates_votes) * 100

        if candidate_votes_percentage > allowed_candidate_votes_percentage:
            return False

    return True


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
