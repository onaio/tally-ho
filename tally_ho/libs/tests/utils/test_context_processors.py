# -*- coding: utf-8 -*-
"""Test libs.utils.context_processors module."""
from django.test import RequestFactory, TestCase


from tally_ho.libs.utils.context_processors import (
    is_superadmin,
    is_tallymanager,
)


class TestContextProcessor(TestCase):
    """Test tally_ho.libs.utils.context_processors functions."""

    def test_is_superadmin(self):
        """Test is_superadmin() context processor function."""
        request = RequestFactory().get("/")
        result = is_superadmin(request)
        self.assertEqual(result, {'is_superadmin': False})

    def test_is_tallymanager(self):
        """Test is_tallymanager() context processor function."""
        request = RequestFactory().get("/")
        result = is_tallymanager(request)
        self.assertEqual(result, {'is_tallymanager': False})
