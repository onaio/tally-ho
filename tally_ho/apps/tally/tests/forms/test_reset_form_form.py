from django import forms as django_forms
from django.test import TestCase

from tally_ho.apps.tally.forms.reset_form_form import ResetFormForm
from tally_ho.libs.tests.test_base import create_result_form, create_tally


class TestResetFormForm(TestCase):
    def setUp(self):
        """Set up test data"""
        self.tally = create_tally()
        self.barcode = '12345678901'
        self.result_form = create_result_form(
            barcode=self.barcode,
            tally=self.tally
        )

    def test_form_valid_with_correct_barcode(self):
        """Test form is valid with correct 11-digit barcode"""
        form_data = {
            'barcode': self.barcode,
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_barcode(self):
        """Test form is invalid when barcode is missing"""
        form_data = {
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)
        self.assertIn(
            'This field is required', 
            form.errors['barcode'][0]
        )

    def test_form_invalid_with_empty_barcode(self):
        """Test form is invalid with empty barcode"""
        form_data = {
            'barcode': '',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)

    def test_form_invalid_with_short_barcode(self):
        """Test form is invalid with barcode less than 11 digits"""
        form_data = {
            'barcode': '12345',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)

    def test_form_invalid_with_long_barcode(self):
        """Test form is invalid with barcode more than 11 digits"""
        form_data = {
            'barcode': '123456789012',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)

    def test_form_invalid_with_non_numeric_barcode(self):
        """Test form is invalid with non-numeric characters"""
        form_data = {
            'barcode': '1234567890a',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)
        self.assertIn(
            'Please enter exactly 11 numbers', 
            str(form.errors['barcode'])
        )

    def test_form_invalid_with_special_characters(self):
        """Test form is invalid with special characters"""
        form_data = {
            'barcode': '12345-67890',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)
        self.assertIn(
            'Please enter exactly 11 numbers', 
            str(form.errors['barcode'])
        )

    def test_form_invalid_with_spaces(self):
        """Test form is invalid with spaces in barcode"""
        form_data = {
            'barcode': '123 456 7890',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('barcode', form.errors)

    def test_form_has_autofocus_attribute(self):
        """Test barcode field has autofocus attribute"""
        form = ResetFormForm()
        self.assertEqual(
            form.fields['barcode'].widget.attrs.get('autofocus'),
            'on'
        )

    def test_form_has_security_attributes(self):
        """Test barcode field has security attributes 
        to prevent copy/paste"""
        form = ResetFormForm()
        attrs = form.fields['barcode'].widget.attrs

        self.assertEqual(attrs.get('oncopy'), 'return false;')
        self.assertEqual(attrs.get('onpaste'), 'return false;')
        self.assertEqual(attrs.get('ondrag'), 'return false;')
        self.assertEqual(attrs.get('ondrop'), 'return false;')
        self.assertEqual(attrs.get('autocomplete'), 'off')

    def test_form_has_input_validation_attribute(self):
        """Test barcode field has oninput validation for numbers only"""
        form = ResetFormForm()
        attrs = form.fields['barcode'].widget.attrs

        self.assertIn('oninput', attrs)
        self.assertEqual(
            attrs.get('oninput'),
            "this.value = this.value.replace(/[^0-9]/g, '')"
        )

    def test_form_has_correct_css_class(self):
        """Test barcode field has correct CSS class"""
        form = ResetFormForm()
        self.assertEqual(
            form.fields['barcode'].widget.attrs.get('class'),
            'form-control'
        )

    def test_form_has_correct_title(self):
        """Test barcode field has correct title attribute"""
        form = ResetFormForm()
        self.assertEqual(
            form.fields['barcode'].widget.attrs.get('title'),
            'Please enter exactly 11 numbers'
        )

    def test_form_tally_id_is_hidden(self):
        """Test tally_id field is a hidden input"""
        form = ResetFormForm()
        self.assertIsInstance(
            form.fields['tally_id'].widget,
            django_forms.HiddenInput
        )

    def test_save_returns_result_form_when_valid(self):
        """Test save method returns ResultForm when form is valid"""
        form_data = {
            'barcode': self.barcode,
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertTrue(form.is_valid())

        result = form.save()
        self.assertEqual(result.barcode, self.barcode)
        self.assertEqual(result.tally.id, self.tally.id)
        self.assertEqual(result, self.result_form)

    def test_save_raises_validation_error_when_form_not_found(self):
        """Test save raises ValidationError when ResultForm 
        doesn't exist"""
        form_data = {
            'barcode': '99999999999',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertTrue(form.is_valid())

        with self.assertRaises(django_forms.ValidationError) as context:
            form.save()

        self.assertIn('Form not found', str(context.exception))

    def test_save_raises_validation_error_when_tally_mismatch(self):
        """Test save raises ValidationError when tally doesn't match"""
        other_tally = create_tally(name="otherTally")

        form_data = {
            'barcode': self.barcode,
            'tally_id': other_tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertTrue(form.is_valid())

        with self.assertRaises(django_forms.ValidationError) as context:
            form.save()

        self.assertIn('Form not found', str(context.exception))

    def test_save_does_not_execute_when_form_invalid(self):
        """Test save method returns None when form is invalid"""
        form_data = {
            'barcode': 'invalid',
            'tally_id': self.tally.id
        }
        form = ResetFormForm(data=form_data)
        self.assertFalse(form.is_valid())

        result = form.save()
        self.assertIsNone(result)

    def test_barcode_field_is_required(self):
        """Test barcode field is marked as required"""
        form = ResetFormForm()
        self.assertTrue(form.fields['barcode'].required)

    def test_barcode_field_has_correct_min_max_length(self):
        """Test barcode field has correct min and max length"""
        form = ResetFormForm()
        self.assertEqual(form.fields['barcode'].min_length, 11)
        self.assertEqual(form.fields['barcode'].max_length, 11)

    def test_barcode_field_label(self):
        """Test barcode field has correct label"""
        form = ResetFormForm()
        self.assertEqual(form.fields['barcode'].label, 'Form Barcode')
