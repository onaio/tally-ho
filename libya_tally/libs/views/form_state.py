from django.core.exceptions import SuspiciousOperation
from django.utils.translation import ugettext as _

from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.views.errors import add_generic_error


def listify(maybe_list):
    """Make maybe list a list if it is not.

    :param maybe_list: A variable that may be a list.

    :returns: A list."""
    return [maybe_list] if not isinstance(maybe_list, list) else maybe_list


def safe_form_in_state(result_form, states, form):
    """Check form in state and add an error to form if not in the correct
    state.

    :param result_form: The result form to check the state of.
    :param states: The allowable states for the form.
    :param form: The form to add an error message to if any exist.

    :returns: Form with an error message or None.
    """
    try:
        form_in_state(result_form, states)
    except SuspiciousOperation as e:
        return add_generic_error(form, str(e))


def form_in_state(result_form, states):
    """Raise a SuspiciousOperation if result form is not in an allowable state.

    :param result_form: The result form to check the state of.
    :param states: The allowable states.

    :raises: `SuspiciousOperation` if form not in one of states.
    :returns: True if form is in an allowable state.
    """
    states = listify(states)

    if not result_form.form_state in states:
        state_names = get_state_names(states)

        raise SuspiciousOperation(
            _(u"Form not in %(state_name)s.  Return form to %(state)s"
              % {'state_name': state_names,
                 'state': result_form.form_state_name}))

    return True


def form_in_data_entry_state(result_form):
    """Check that result form is in a data entry state."""
    return form_in_state(result_form, [
        FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_2])


def form_in_intake_state(result_form):
    """Check that result form is in intake state."""
    return form_in_state(result_form, [FormState.INTAKE])


def get_state_names(states):
    """Get a string of labels for states.

    :param states: The states to get labels for.

    :returns: A string of state names join with 'or'
    """
    states = listify(states)
    state_names = [str(FormState.label(s)) for s in states]

    return " or ".join(state_names)
