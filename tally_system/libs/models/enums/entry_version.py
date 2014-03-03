from django_enumfield import enum


class EntryVersion(enum.Enum):
    DATA_ENTRY_1 = 0
    DATA_ENTRY_2 = 1
    FINAL = 2
