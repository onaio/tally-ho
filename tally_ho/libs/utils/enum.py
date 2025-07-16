import enum


class Enum(enum.Enum):
    @classmethod
    def choices(cls):
        return cls.CHOICES.value

    @property
    def label(self):
        return ' '.join(map(lambda x: x.capitalize(), self.name.split('_')))


def get_matching_enum_values(enum_class, search_string):
    """
    Return enum values where search_string is case-insensitively contained
    in either the enum name or label representation.

    Args:
        enum_class: The enum class to search through
        search_string: The string to search for (case-insensitive)

    Returns:
        List of enum values that match the search criteria
    """
    if not search_string:
        return []

    matching_values = []
    search_lower = search_string.strip().lower()

    for enum_value in enum_class:
        # Check both the enum name and label
        if (search_lower in enum_value.name.lower() or
            search_lower in enum_value.label.lower()):
            matching_values.append(enum_value)

    return matching_values
