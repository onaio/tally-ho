from django.utils.translation import ugettext as _

from libya_tally.libs.models.enums.form_state import FormState


def form_in_state(result_form, states):
    if not result_form.form_state in states:
        raise Exception(
            _(u"Result Form not in %s state, form in state '%s'"
              % (" ".join(states), result_form.form_state_name)))

    return True


def form_in_data_entry_state(result_form):
    return form_in_state(result_form, [
        FormState.DATA_ENTRY_1, FormState.DATA_ENTRY_1])


def form_in_intake_state(result_form):
    return form_in_state(result_form, [FormState.INTAKE])
