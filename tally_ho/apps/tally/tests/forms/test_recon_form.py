from tally_ho.apps.tally.forms.recon_form import ReconForm
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import TestBase, create_result_form


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
            'number_invalid_votes': 0,
            'number_valid_votes': 100,
            'number_sorted_and_counted': 100,
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

    def test_disable_copy_paste_attributes(self):
        """Test that the copy/paste attributes are disabled on all
        form fields."""
        form = ReconForm()
        for field in form.fields.values():
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
        for field in form.fields.values():
            if field.required:
                self.assertIn('required', field.widget.attrs.get('class', ''))
