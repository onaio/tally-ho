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
        CLEARANCE: (INTAKE, UNSUBMITTED, CORRECTION,
                    ARCHIVED, DATA_ENTRY_1, DATA_ENTRY_2, QUALITY_CONTROL),
        CORRECTION: (DATA_ENTRY_2,),
        DATA_ENTRY_1: (AUDIT, CORRECTION, INTAKE, QUALITY_CONTROL),
        DATA_ENTRY_2: (DATA_ENTRY_1,),
        INTAKE: (CLEARANCE, UNSUBMITTED),
        QUALITY_CONTROL: (CORRECTION,),
        UNSUBMITTED: (CLEARANCE, INTAKE),
    }
