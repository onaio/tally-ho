from django import forms
from tally_ho.apps.tally.forms.fields import RestrictedFileField

ALLOWED_FILE_EXTENTIONS = ['.csv']


class TallyFilesForm(forms.Form):
    subconst_file =\
        RestrictedFileField(label='Subconstituency file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    centers_file =\
        RestrictedFileField(label='Centers file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    stations_file =\
        RestrictedFileField(label='Stations file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    candidates_file =\
        RestrictedFileField(label='Candidates file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    ballots_order_file =\
        RestrictedFileField(label='Ballot order file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    result_forms_file =\
        RestrictedFileField(label='Result forms file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    tally_id = forms.IntegerField(widget=forms.HiddenInput())
