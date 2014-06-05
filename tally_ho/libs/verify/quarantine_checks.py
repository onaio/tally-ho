from django.utils.translation import ugettext as _
from tally_ho.apps.tally.models.quarantine_check import\
    QuarantineCheck


def create_quarantine_checks():
    quarantine_data = [
        [_('Trigger 1 - Guard against overvoting'), 'pass_overvote', 10],
        [_('Trigger 2 - Guard against errors and tampering with the form'),
         'pass_tampering', 3]
    ]

    for name, method, value in quarantine_data:
        QuarantineCheck.objects.get_or_create(
            name=name, method=method, value=value)


def quarantine_checks():
    """Return tuples of (QuarantineCheck, validation_function)."""
    methods = [pass_overvote, pass_tampering]
    checks = QuarantineCheck.objects.all().order_by('pk')

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
    max_number_ballots = registrants + qc.value

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
    # TODO Check if 'qc' variable must be QuarantineCheck object with method 'pass_tampering' or not
    qc = QuarantineCheck.objects.get(method='pass_tampering')
    scaled_tolerance = (qc.value / 100) * (
        num_votes + number_ballots_expected) / 2

    return diff <= scaled_tolerance
