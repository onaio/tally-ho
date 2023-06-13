def capitalize_first_letter(s):
    """
    Capitalize the first letter of the string and convert the remaining letters
    to lowercase.

    :param: s (str): The input string.
    :returns: str: The modified string with the first letter capitalized
    and the rest in lowercase.
    """
    return s[:1].upper() + s[1:].lower()
