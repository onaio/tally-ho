from django.test import TestCase

from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.utils.enum import get_matching_enum_values


class TestGetMatchingEnumValues(TestCase):
    """Test cases for get_matching_enum_values utility function."""

    def test_empty_search_string_returns_empty_list(self):
        """Test that empty search string returns empty list."""
        result = get_matching_enum_values(FormState, "")
        self.assertEqual(result, [])

    def test_none_search_string_returns_empty_list(self):
        """Test that None search string returns empty list."""
        result = get_matching_enum_values(FormState, None)
        self.assertEqual(result, [])

    def test_case_insensitive_enum_name_matching(self):
        """Test case-insensitive matching on enum names."""
        # Test uppercase search
        result = get_matching_enum_values(FormState, "AUDIT")
        self.assertIn(FormState.AUDIT, result)

        # Test lowercase search
        result = get_matching_enum_values(FormState, "audit")
        self.assertIn(FormState.AUDIT, result)

        # Test mixed case search
        result = get_matching_enum_values(FormState, "AuDiT")
        self.assertIn(FormState.AUDIT, result)

    def test_partial_enum_name_matching(self):
        """Test partial matching on enum names."""
        # Search for "entry" should match DATA_ENTRY_1 and DATA_ENTRY_2
        result = get_matching_enum_values(FormState, "entry")
        self.assertIn(FormState.DATA_ENTRY_1, result)
        self.assertIn(FormState.DATA_ENTRY_2, result)

        # Search for "data" should match DATA_ENTRY_1 and DATA_ENTRY_2
        result = get_matching_enum_values(FormState, "data")
        self.assertIn(FormState.DATA_ENTRY_1, result)
        self.assertIn(FormState.DATA_ENTRY_2, result)

        # Search for "quality" should match QUALITY_CONTROL
        result = get_matching_enum_values(FormState, "quality")
        self.assertIn(FormState.QUALITY_CONTROL, result)

    def test_label_matching(self):
        """Test matching on enum labels."""
        # FormState.DATA_ENTRY_1.label would be "Data Entry 1"
        # So searching for "Entry" should match
        result = get_matching_enum_values(FormState, "Entry")
        self.assertIn(FormState.DATA_ENTRY_1, result)
        self.assertIn(FormState.DATA_ENTRY_2, result)

        # Searching for "Quality Control" should match QUALITY_CONTROL
        result = get_matching_enum_values(FormState, "Quality Control")
        self.assertIn(FormState.QUALITY_CONTROL, result)

        # Searching for "Control" should match QUALITY_CONTROL
        result = get_matching_enum_values(FormState, "Control")
        self.assertIn(FormState.QUALITY_CONTROL, result)

    def test_case_insensitive_label_matching(self):
        """Test case-insensitive matching on enum labels."""
        # Test lowercase search on labels
        result = get_matching_enum_values(FormState, "quality control")
        self.assertIn(FormState.QUALITY_CONTROL, result)

        # Test uppercase search on labels
        result = get_matching_enum_values(FormState, "QUALITY CONTROL")
        self.assertIn(FormState.QUALITY_CONTROL, result)

        # Test mixed case search on labels
        result = get_matching_enum_values(FormState, "QuAlItY cOnTrOl")
        self.assertIn(FormState.QUALITY_CONTROL, result)

    def test_no_matches_returns_empty_list(self):
        """Test that no matches returns empty list."""
        result = get_matching_enum_values(FormState, "nonexistent")
        self.assertEqual(result, [])

        result = get_matching_enum_values(FormState, "zzz")
        self.assertEqual(result, [])

    def test_exact_enum_name_matching(self):
        """Test exact enum name matching."""
        result = get_matching_enum_values(FormState, "ARCHIVED")
        self.assertIn(FormState.ARCHIVED, result)
        self.assertEqual(len(result), 1)

        result = get_matching_enum_values(FormState, "UNSUBMITTED")
        self.assertIn(FormState.UNSUBMITTED, result)
        self.assertEqual(len(result), 1)

    def test_multiple_matches(self):
        """Test searches that return multiple matches."""
        # Search for "entry" should return both DATA_ENTRY_1 and DATA_ENTRY_2
        result = get_matching_enum_values(FormState, "entry")
        self.assertIn(FormState.DATA_ENTRY_1, result)
        self.assertIn(FormState.DATA_ENTRY_2, result)
        self.assertEqual(len(result), 2)

        # Search for "data" should return both DATA_ENTRY_1 and DATA_ENTRY_2
        result = get_matching_enum_values(FormState, "data")
        self.assertIn(FormState.DATA_ENTRY_1, result)
        self.assertIn(FormState.DATA_ENTRY_2, result)
        self.assertEqual(len(result), 2)

    def test_single_character_search(self):
        """Test single character searches."""
        # Search for "A" should match ARCHIVED, AUDIT
        result = get_matching_enum_values(FormState, "A")
        self.assertIn(FormState.ARCHIVED, result)
        self.assertIn(FormState.AUDIT, result)

        # Search for "C" should match CLEARANCE, CORRECTION, QUALITY_CONTROL
        result = get_matching_enum_values(FormState, "C")
        self.assertIn(FormState.CLEARANCE, result)
        self.assertIn(FormState.CORRECTION, result)
        self.assertIn(FormState.QUALITY_CONTROL, result)

    def test_whitespace_handling(self):
        """Test handling of whitespace in search strings."""
        # Search with leading/trailing whitespace
        result = get_matching_enum_values(FormState, "  audit  ")
        self.assertIn(FormState.AUDIT, result)

        # Search with internal whitespace should match labels
        result = get_matching_enum_values(FormState, "quality control")
        self.assertIn(FormState.QUALITY_CONTROL, result)

    def test_special_characters(self):
        """Test handling of special characters."""
        # Search for underscore should match enum names with underscores
        result = get_matching_enum_values(FormState, "_")
        # Should match all enum values that have underscores in their names
        self.assertIn(FormState.DATA_ENTRY_1, result)
        self.assertIn(FormState.DATA_ENTRY_2, result)
        self.assertIn(FormState.QUALITY_CONTROL, result)

    def test_number_matching(self):
        """Test matching on numbers in enum names."""
        # Search for "1" should match DATA_ENTRY_1
        result = get_matching_enum_values(FormState, "1")
        self.assertIn(FormState.DATA_ENTRY_1, result)
        self.assertEqual(len([
            x for x in result
            if x == FormState.DATA_ENTRY_1
        ]), 1)

        # Search for "2" should match DATA_ENTRY_2
        result = get_matching_enum_values(FormState, "2")
        self.assertIn(FormState.DATA_ENTRY_2, result)
        self.assertEqual(len([
            x for x in result
            if x == FormState.DATA_ENTRY_2
        ]), 1)
