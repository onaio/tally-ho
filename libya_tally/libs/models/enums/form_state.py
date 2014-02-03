from django_enumfield import enum


class FormState(enum.Enum):
    ARCHIVED = 0
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
        ARCHIVED: (ARCHIVING, AUDIT),
        ARCHIVING: (QUALITY_CONTROL,),
        AUDIT: (ARCHIVING,),
        CLEARANCE: (INTAKE,),
        CORRECTION: (DATA_ENTRY_2),
        DATA_ENTRY_1: (AUDIT, CORRECTION, INTAKE, QUALITY_CONTROL),
        DATA_ENTRY_2: (DATA_ENTRY_1),
        INTAKE: (CLEARANCE, UNSUBMITTED,),
        QUALITY_CONTROL: (CORRECTION),
    }

    @classmethod
    def to_name(cls, enum):
        return dict(cls.choices())[enum]
