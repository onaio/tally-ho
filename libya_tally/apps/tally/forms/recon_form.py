from django.forms import ModelForm
from libya_tally.apps.tally.models import ReconciliationForm


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
        fields = ['ballot_number_from',
                  'ballot_number_to',
                  'number_ballots_received',
                  'number_signatures_in_vr',
                  'number_unused_ballots',
                  'number_spoiled_ballots',
                  'number_cancelled_ballots',
                  'number_ballots_outside_box',
                  'number_ballots_inside_box',
                  'number_ballots_inside_and_outside_box',
                  'number_unstamped_ballots',
                  'number_invalid_votes',
                  'number_valid_votes',
                  'number_sorted_and_counted',
                  'remarks']
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ReconForm, self).__init__(*args, **kwargs)
        self.fields['ballot_number_from'].widget.attrs['autofocus'] = 'on'
        for field in self.fields:
            for k, v in disable_copy_input.iteritems():
                self.fields[field].widget.attrs[k] = v
