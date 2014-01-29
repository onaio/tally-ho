from django_enumfield import enum


class FormType(enum.Enum):
    OCV = 0
    RESULTS_AND_RECONCILIATION = 1
    SPECIAL = 2
