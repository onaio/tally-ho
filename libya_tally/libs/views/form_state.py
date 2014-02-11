from django.core.exceptions import SuspiciousOperation
from django.utils.translation import ugettext as _

from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.views.errors import add_generic_error


def safe_form_in_state(result_form, states, form):
    try:
        form_in_state(result_form, states)
    except SuspiciousOperation:
        state_names = get_state_names(states)
        message = _(u"Form not in %(state_name)s.  Return form to %(state)s"
                    % {'state_name': state_names,
                       'state': result_form.form_state_name})
        return add_generic_error(form, message)


def form_in_state(result_form, states):
    if not isinstance(states, list):
        states = [states]

    if not result_form.form_state in states:
        state_names = get_state_names(states)

        raise SuspiciousOperation(
            _(u"Form not in %(state_name)s.  Return form to %(state)s"
              % {'state_name': state_names,
                 'state': result_form.form_state_name}))

    return True


def form_in_data_entry_state(result_form):
    return form_in_state(result_form, [
        FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_2])


def form_in_intake_state(result_form):
    return form_in_state(result_form, [FormState.INTAKE])


def get_state_names(states):
    if not isinstance(states, list):
        states = [states]

    state_names = [str(FormState.to_name(s)) for s in states]
    return " or ".join(state_names)
