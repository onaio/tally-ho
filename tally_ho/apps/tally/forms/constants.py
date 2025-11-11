"""
Form constants and shared configurations.

This module contains constants used across multiple form files to avoid
code duplication and ensure consistency.
"""

# Attributes to disable copy/paste operations on form fields.
# Used for sensitive fields where manual entry is required for accuracy
# and security (e.g., barcodes, station numbers, vote counts).
DISABLE_COPY_INPUT = {
    "onCopy": "return false;",
    "onDrag": "return false;",
    "onDrop": "return false;",
    "onPaste": "return false;",
    "autocomplete": "off",
    "class": "form-control",
}
