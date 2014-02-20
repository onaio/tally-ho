from django_enumfield import enum


class AuditResolution(enum.Enum):
    NO_PROBLEM_TO_DE_1 = 1
    CLARIFIED_FIGURES_TO_DE_1 = 2
    OTHER_CORRECTION_TO_DE_1 = 3
    MAKE_AVAILABLE_FOR_ARCHIVE = 4
