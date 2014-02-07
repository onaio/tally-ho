from libya_tally.apps.tally.models.quarantine_check import\
    QuarantineCheck
from libya_tally.apps.tally.models.reconciliation_form import\
    ReconciliationForm


def create_quarantine_checks():
    quarantine_data = [
        ['Trigger 1 - Guard against overvoting', 'pass_overvote', 10],
        ['Trigger 2 - Guard against errors and tampering with the form',
         'pass_tampering', 5]
    ]

    for name, method, value in quarantine_data:
        QuarantineCheck.objects.create(name=name, method=method, value=value)


def quarantine_checks():
    methods = [pass_overvote, pass_tampering]
    checks = QuarantineCheck.objects.all().order_by('pk')
    """Return tuples of (QuarantineCheck, validation_function)."""
    return zip(methods, checks)


def pass_overvote(result_form):
    """Check to guard against overvoting.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    Fails if the number of ballots reported to be used in a station exceeds
    the number of potential voters minus the number of registrants plus N
    persons to accomodate staff and security.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    try:
        recon_form = result_form.reconciliation_form
    except ReconciliationForm.DoesNotExists:
        return True

    qc = QuarantineCheck.get(method='pass_overvote')
    expected_number_ballots =\
        result_form.station.result_form.station.registrants + qc.value

    return recon_form.number_ballots_used <= expected_number_ballots


def pass_tampering(result_form):
    """Guard against errors and tampering with the form.

    If the `result_form` does not have a `reconciliation_form` this will
    always return True.

    Fails in sum of the results section of the form does not equal the number
    of ballots expected based on the calculation of the key fields from the
    reconciliation form with a N% tolerance.

    :param result_form: The result form to check.
    :returns: A boolean of true if passed, otherwise false.
    """
    try:
        recon_form = result_form.reconciliation_form
    except ReconciliationForm.DoesNotExists:
        return True

    num_votes = result_form.num_votes
    number_ballots_expected = recon_form.number_ballots_expected
    diff = abs(num_votes - number_ballots_expected)
    qc = QuarantineCheck.get(method='pass_overvote')

    return diff > (qc.value / 100) * num_votes + number_ballots_expected
