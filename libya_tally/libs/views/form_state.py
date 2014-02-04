from django.core.exceptions import SuspiciousOperation
from django.forms.util import ErrorList
from django.utils.translation import ugettext as _

from libya_tally.libs.models.enums.form_state import FormState


def safe_form_in_state(result_form, states, form):
    try:
        form_in_state(result_form, states)
    except SuspiciousOperation:
        state_names = get_state_names(states)
        errors = form._errors.setdefault("__all__", ErrorList())
        errors.append(_(u"Form not in %s.  Return form to %s"
                        % (state_names, result_form.form_state_name)))

        return form


def form_in_state(result_form, states):
    if not isinstance(states, list):
        states = [states]

    if not result_form.form_state in states:
        state_names = get_state_names(states)

        raise SuspiciousOperation(
            _(u"Result Form not in %s state, form in state '%s'"
              % (state_names, result_form.form_state_name)))

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
