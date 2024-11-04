from tally_ho.libs.tests.test_base import TestBase, create_result_form
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.forms.recon_form import ReconForm
from django.utils.translation import gettext_lazy as _

class ReconFormTest(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.result_form = create_result_form()
        # Default valid data for the form
        self.valid_data = {
            'result_form': self.result_form,
            'user': self.user,
            'is_stamped': True,
            'number_ballots_received': 100,
            'number_of_voter_cards_in_the_ballot_box': 100,
            'number_unused_ballots': 0,
            'number_spoiled_ballots': 0,
            'number_cancelled_ballots': 0,
            'number_ballots_outside_box': 0,
            'number_ballots_inside_box': 100,
            'number_ballots_inside_and_outside_box': 100,
            'total_of_cancelled_ballots_and_ballots_inside_box': 100,
            # Should match 5 + 7
            'number_unstamped_ballots': 0,
            'number_invalid_votes': 0,
            'number_valid_votes': 100,
            'number_sorted_and_counted': 100,
            'signature_polling_officer_1': True,
            'signature_polling_officer_2': True,
            'signature_polling_station_chair': True,
            'signature_dated': True,
        }

    def test_valid_data(self):
        """Test that the form is valid with correct data."""
        form = ReconForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        """Test that the form is invalid when required fields are missing."""
        invalid_data = self.valid_data.copy()
        invalid_data.pop('number_valid_votes')  # Remove a required field
        form = ReconForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('number_valid_votes', form.errors)

    def test_custom_clean_validation(self):
        """Test that custom validation in clean method raises error with
        incorrect totals."""
        invalid_data = self.valid_data.copy()
        invalid_data['total_of_cancelled_ballots_and_ballots_inside_box'] =\
            999  # Invalid total
        form = ReconForm(data=invalid_data)
        self.assertFalse(form.is_valid())

        # Convert the error messages to strings for comparison
        error_messages = [str(err) for err in form.errors['__all__']]

        # Check if the expected error message is in the error messages
        self.assertIn(
            str(_('Total of fied 5 and 7 is incorrect')), error_messages)

    def test_disable_copy_paste_attributes(self):
        """Test that the copy/paste attributes are disabled on all
        form fields."""
        form = ReconForm()
        for field_name, field in form.fields.items():
            widget_attrs = field.widget.attrs
            self.assertEqual(widget_attrs.get('onCopy'), 'return false;')
            self.assertEqual(widget_attrs.get('onDrag'), 'return false;')
            self.assertEqual(widget_attrs.get('onDrop'), 'return false;')
            self.assertEqual(widget_attrs.get('onPaste'), 'return false;')
            self.assertEqual(widget_attrs.get('autocomplete'), 'off')
            self.assertIn('form-control', widget_attrs.get('class', ''))

    def test_required_field_class_added(self):
        """Test that 'required' class is added to required fields."""
        form = ReconForm()
        for field_name, field in form.fields.items():
            if field.required:
                self.assertIn('required', field.widget.attrs.get('class', ''))
