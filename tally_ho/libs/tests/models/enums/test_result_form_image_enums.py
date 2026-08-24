from django.test import TestCase

from tally_ho.libs.models.enums.result_form_image_kind import (
    ResultFormImageKind,
)
from tally_ho.libs.models.enums.result_form_image_source import (
    ResultFormImageSource,
)


class TestResultFormImageSource(TestCase):
    def test_source_values(self):
        self.assertEqual(ResultFormImageSource.UPLOAD.value, 0)
        self.assertEqual(ResultFormImageSource.PVP_IMPORT.value, 1)


class TestResultFormImageKind(TestCase):
    def test_kind_values(self):
        self.assertEqual(ResultFormImageKind.SUPPORTING.value, 0)
        self.assertEqual(ResultFormImageKind.CLERK_SIGNATURE.value, 1)
        self.assertEqual(ResultFormImageKind.FORM_PAGE_1.value, 2)
        self.assertEqual(ResultFormImageKind.FORM_PAGE_2.value, 3)
