import pathlib
from django import forms
from django.utils.translation import ugettext_lazy as _


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

    def clean(self):
        cleaned_data = super(TallyFilesForm, self).clean()
        files = ['subconst_file', 'centers_file',
                 'candidates_file', 'ballots_order_file', 'result_forms_file']
        for file in files:
            file = cleaned_data.get(file, None)
            file_extension = pathlib.Path(file.name).suffix
            if file_extension != '.csv':
                raise forms.ValidationError(
                    _(u'File extension (%s) is not supported.'
                      ' Allowed extensions are .csv') % file_extension)
