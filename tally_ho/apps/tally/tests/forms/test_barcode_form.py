from django.test import TestCase

from tally_ho.apps.tally.forms.barcode_form import ResultFormSearchBarcodeForm


class TestResultFormSearchBarcodeForm(TestCase):
    def test_form_valid_with_numeric_barcode(self):
        """Test form is valid with numeric barcode"""
        form_data = {
            'barcode': '12345',
            'tally_id': 1
        }
        form = ResultFormSearchBarcodeForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_barcode(self):
        """Test form is invalid when barcode is missing"""
        form_data = {
            'tally_id': 1
        }
        form = ResultFormSearchBarcodeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)
        self.assertIn('This field is required', form.errors['barcode'][0])

    def test_form_invalid_with_empty_barcode(self):
        """Test form is invalid with empty barcode"""
        form_data = {
            'barcode': '',
            'tally_id': 1
        }
        form = ResultFormSearchBarcodeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)

    def test_form_invalid_with_non_numeric_barcode(self):
        """Test form is invalid with non-numeric characters"""
        form_data = {
            'barcode': '123abc',
            'tally_id': 1
        }
        form = ResultFormSearchBarcodeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)
        self.assertIn('Expecting only numbers', str(form.errors['barcode']))

    def test_form_invalid_with_special_characters(self):
        """Test form is invalid with special characters"""
        form_data = {
            'barcode': '123-456',
            'tally_id': 1
        }
        form = ResultFormSearchBarcodeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)

    def test_form_valid_with_long_numeric_barcode(self):
        """Test form accepts long numeric barcodes"""
        form_data = {
            'barcode': '123456789012345',
            'tally_id': 1
        }
        form = ResultFormSearchBarcodeForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_has_autofocus_attribute(self):
        """Test barcode field has autofocus attribute"""
        form = ResultFormSearchBarcodeForm()
        self.assertEqual(
            form.fields['barcode'].widget.attrs.get('autofocus'),
            'on'
        )

    def test_form_has_security_attributes(self):
        """Test barcode field has security attributes"""
        form = ResultFormSearchBarcodeForm()
        attrs = form.fields['barcode'].widget.attrs

        self.assertEqual(attrs.get('onCopy'), 'return false;')
        self.assertEqual(attrs.get('onPaste'), 'return false;')
        self.assertEqual(attrs.get('autocomplete'), 'off')
        self.assertEqual(attrs.get('class'), 'form-control')
