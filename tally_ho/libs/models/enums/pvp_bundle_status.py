from tally_ho.libs.utils.enum import Enum


class PvpBundleStatus(Enum):
    PENDING = 0
    IMPORTING = 1
    COMPLETED = 2
    FAILED = 3
