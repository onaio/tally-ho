from django import forms


class TallyFilesForm(forms.Form):
    subconst_file = forms.FileField(label='Subconstituency file',
                                    required=True)
    centers_file = forms.FileField(label='Centers file', required=True)
    stations_file = forms.FileField(label='Stations file', required=True)
    candidates_file = forms.FileField(label='Candidates file', required=True)
    ballots_order_file = forms.FileField(label='Ballot order file',
                                         required=True)
    result_forms_file = forms.FileField(label='Result forms file',
                                        required=True)
    tally_id = forms.IntegerField(widget=forms.HiddenInput())
