from tally_ho.libs.utils.enum import Enum


class FormState(Enum):
    ARCHIVED = 0
    # Archiving has been removed from the state table, but we keep it here for
    # compatibility with old databases.
    ARCHIVING = 1
    AUDIT = 2
    CLEARANCE = 3
    CORRECTION = 4
    DATA_ENTRY_1 = 5
    DATA_ENTRY_2 = 6
    INTAKE = 7
    QUALITY_CONTROL = 8
    UNSUBMITTED = 9

    # TODO - can we remove, this does not seem to be used anywhere
    _transitions = {
        ARCHIVED: (QUALITY_CONTROL, AUDIT),
        AUDIT: (CORRECTION, DATA_ENTRY_1, DATA_ENTRY_2,
                ARCHIVED, QUALITY_CONTROL),
        CLEARANCE: (INTAKE, UNSUBMITTED, CORRECTION, AUDIT,
                    ARCHIVED, DATA_ENTRY_1, DATA_ENTRY_2, QUALITY_CONTROL),
        CORRECTION: (DATA_ENTRY_2,),
        DATA_ENTRY_1: (AUDIT, CORRECTION, INTAKE, QUALITY_CONTROL),
        DATA_ENTRY_2: (DATA_ENTRY_1,),
        INTAKE: (CLEARANCE, UNSUBMITTED),
        QUALITY_CONTROL: (CORRECTION,),
        UNSUBMITTED: (CLEARANCE, INTAKE),
    }

    """
    values represent states that a form would already been processed through
    to get to the state used as a key, e.g.
    Forms in intake have to have had passed through states: (unsubmitted
    , clearance, and audit)
    """
    _transitions_before_state = {
        INTAKE: (UNSUBMITTED, CLEARANCE, AUDIT),
        DATA_ENTRY_1: (UNSUBMITTED, INTAKE, CLEARANCE, AUDIT),
        DATA_ENTRY_2: (UNSUBMITTED, INTAKE, DATA_ENTRY_1, CLEARANCE, AUDIT),
        CORRECTION: (UNSUBMITTED, INTAKE, DATA_ENTRY_1, DATA_ENTRY_2,
                     CLEARANCE, AUDIT),
        QUALITY_CONTROL: (UNSUBMITTED, INTAKE, DATA_ENTRY_1, DATA_ENTRY_2,
                          CORRECTION, CLEARANCE, AUDIT),
        ARCHIVED: (UNSUBMITTED, INTAKE, DATA_ENTRY_1, DATA_ENTRY_2,
                   CORRECTION, QUALITY_CONTROL, CLEARANCE, AUDIT),
    }

    @classmethod
    def __publicMembers__(cls):
        return (member for member in cls.__members__.values() if
                isinstance(member.value, int)
                and member != FormState.ARCHIVING)


def processed_states_at_state(form_state):
    """
    If  a form has one of the returned states then it would be considered
    processed relative to the given state.
    """
    if form_state in [FormState.ARCHIVED, FormState.UNSUBMITTED,
                      FormState.ARCHIVED, FormState.CLEARANCE,
                      FormState.AUDIT]:
        return (form_state,)

    ret_val = tuple()
    plausible_unprocessed = un_processed_states_at_state(form_state)
    if plausible_unprocessed:
        ret_val = tuple(
            set(FormState.__publicMembers__()) - set(plausible_unprocessed))
    return ret_val


def un_processed_states_at_state(form_state):
    """
    If  a form is has one of the returned states then it would be considered
    unprocessed relative to the given state.
    Note: some states do not have valid un-processed states e.g. review states
    and un-submitted.
    """
    ret_val = tuple()
    form_state_value = form_state.value
    past_form_states = FormState._transitions_before_state.value.get(
        form_state_value)

    if past_form_states:
        past_form_states = tuple(
            [FormState(alias) for alias in past_form_states]
        )
        if form_state == FormState.ARCHIVED:
            ret_val = ret_val + past_form_states
        else:
            ret_val = ret_val + (form_state,) + past_form_states

    return ret_val
