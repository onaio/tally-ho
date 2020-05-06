from django.conf import settings

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.quarantine_check import\
    QuarantineCheck


def create_quarantine_checks():
    for quarantine_check in getattr(settings, 'QUARANTINE_DATA'):
        QuarantineCheck.objects.get_or_create(
            name=quarantine_check['name'],
            method=quarantine_check['method'],
            value=quarantine_check['value'],
            percentage=quarantine_check['percentage']
        )


def quarantine_checks():
    """Return tuples of (QuarantineCheck, validation_function)."""
    all_methods =\
        {'pass_overvote': pass_overvote,
         'pass_tampering': pass_tampering,
         'pass_ballots_number_validation': pass_ballots_number_validation,
         'pass_signatures_validation': pass_signatures_validation}
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
    total of the ballots inside plus ballots outside.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    recon_form = result_form.reconciliationform

    if not recon_form:
        return True

    ballots_inside_and_outside =\
        recon_form.number_ballots_inside + recon_form.number_ballots_outside
    number_ballots_received = recon_form.number_ballots_received
    diff = abs(number_ballots_received - ballots_inside_and_outside)
    qc = QuarantineCheck.objects.get(method='pass_ballots_number_validation')
    scaled_tolerance = (qc.value / 100) * (
        number_ballots_received + ballots_inside_and_outside) / 2

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

    ballots_inside_and_cancelled =\
        recon_form.number_ballots_inside + recon_form.number_cancelled_ballots
    number_signatures_in_vr = recon_form.number_signatures_in_vr
    diff = abs(number_signatures_in_vr - ballots_inside_and_cancelled)
    qc = QuarantineCheck.objects.get(method='pass_signatures_validation')
    scaled_tolerance = (qc.value / 100) * (
        number_signatures_in_vr + ballots_inside_and_cancelled) / 2

    return diff <= scaled_tolerance


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
