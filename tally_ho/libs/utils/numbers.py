def rounded_safe_div_percent(numerator, denominator, precision=2, default=100):
    return round(100 * (numerator / denominator) if denominator else 100, 2)

def parse_int(s):
    """
    Parses a string to an integer and handles parse errors.

    Args:
        s (str): The string to parse.

    Returns:
        int: The parsed integer, or None if the string could not be parsed.
    """
    try:
        return int(s)
    except Exception:
        return None
