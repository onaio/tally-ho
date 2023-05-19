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

    _transitions_before_state = {
        INTAKE: (UNSUBMITTED, CLEARANCE, AUDIT),
        DATA_ENTRY_1: (UNSUBMITTED, INTAKE, CLEARANCE, AUDIT),
        DATA_ENTRY_2: (UNSUBMITTED, INTAKE, DATA_ENTRY_1, CLEARANCE, AUDIT),
        CORRECTION:   (UNSUBMITTED, INTAKE, DATA_ENTRY_1, DATA_ENTRY_2,
                       CLEARANCE, AUDIT),
        QUALITY_CONTROL: (UNSUBMITTED, INTAKE, DATA_ENTRY_1, DATA_ENTRY_2,
                          CORRECTION, CLEARANCE, AUDIT),
        ARCHIVED: (UNSUBMITTED, INTAKE, DATA_ENTRY_1, DATA_ENTRY_2,
                   QUALITY_CONTROL, CLEARANCE, AUDIT),
    }



# form state progression excluding review stages form states
form_state_shift_path = (
    FormState.UNSUBMITTED, FormState.INTAKE, FormState.DATA_ENTRY_1,
    FormState.DATA_ENTRY_2,FormState.CORRECTION, FormState.QUALITY_CONTROL,
    FormState.ARCHIVING, FormState.ARCHIVED)

# form states that are after the current result form state
def states_transitions_after_result_form_state(form_state):
    states = []
    if FormState._transitions_before_state.value.get(form_state.value):
        for state in FormState:
            # state != form_state so that we don't include current form state
            if isinstance(state.value, int) and state != form_state:
                if state.value not in list(
                FormState._transitions_before_state.value.get(
                    form_state.value)):
                    states.append(state)

    return states

# form states that are before and in the current result form state
def states_transitions_before_result_form_state(form_state):
    states = []
    if FormState._transitions_before_state.value.get(form_state.value):
        for state in FormState:
            if isinstance(state.value, int):
                # state != FormState.ARCHIVED because it's the final stage
                if state.value in list(
                FormState._transitions_before_state.value.get(form_state.value)
                ) or (state == form_state and state != FormState.ARCHIVED):
                    states.append(state)

    return states
