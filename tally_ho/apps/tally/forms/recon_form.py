from django import forms
from django.forms import ModelForm
from tally_ho.apps.tally.models import ReconciliationForm
from django.utils.translation import gettext_lazy as _


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class ReconForm(ModelForm):
    class Meta:
        model = ReconciliationForm
        fields = localized_fields =\
            ['is_stamped',
            'number_ballots_received',
            'number_of_voter_cards_in_the_ballot_box',
            'number_unused_ballots',
            'number_spoiled_ballots',
            'number_cancelled_ballots',
            'number_ballots_outside_box',
            'number_ballots_inside_box',
            'number_ballots_inside_and_outside_box',
            'total_of_cancelled_ballots_and_ballots_inside_box',
            'number_unstamped_ballots',
            'number_invalid_votes',
            'number_valid_votes',
            'number_sorted_and_counted',
            'signature_polling_officer_1',
            'signature_polling_officer_2',
            'signature_polling_station_chair',
            'signature_dated']
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ReconForm, self).__init__(*args, **kwargs)

        for field in self.fields:
            for k, v in list(disable_copy_input.items()):
                self.fields[field].widget.attrs[k] = v

            if self.fields[field].required:
                class_str = 'required'

                if self.fields[field].widget.attrs.get('class'):
                    class_str = '%s %s' % (
                        class_str,
                        self.fields[field].widget.attrs.get('class'))
                self.fields[field].widget.attrs['class'] = class_str
    def clean(self):
        """Verify that the total of field number_cancelled_ballots and
        field number_ballots_inside_box match the value of field
        total_of_cancelled_ballots_and_ballots_inside_box
        """
        if self.is_valid():
            cleaned_data = super(ReconForm, self).clean()
            number_cancelled_ballots =\
                cleaned_data.get('number_cancelled_ballots')
            number_ballots_inside_box =\
                cleaned_data.get('number_ballots_inside_box')
            total_of_cancelled_ballots_and_ballots_inside_box =\
                cleaned_data.get(
                    'total_of_cancelled_ballots_and_ballots_inside_box')

            if (number_cancelled_ballots + number_ballots_inside_box) !=\
                total_of_cancelled_ballots_and_ballots_inside_box:
                raise forms.ValidationError(
                    _('Total of fied 5 and 7 is incorrect'))
            return cleaned_data
