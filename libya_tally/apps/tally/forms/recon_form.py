from django.forms import ModelForm
from libya_tally.apps.tally.models import ReconciliationForm


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
