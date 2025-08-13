from django import forms

from tally_ho.apps.tally.forms.fields import RestrictedFileField

ALLOWED_FILE_EXTENTIONS = ['.csv']


class TallyFilesForm(forms.Form):
    ballots_file =\
        RestrictedFileField(label='Ballots file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    subconst_file =\
        RestrictedFileField(label='Subconstituency file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    subconst_ballots_file =\
        RestrictedFileField(label='Subconstituency ballots file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    centers_file =\
        RestrictedFileField(label='Centers file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    stations_file =\
        RestrictedFileField(label='Stations file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    candidates_file =\
        RestrictedFileField(label='Candidates file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    ballots_order_file =\
        RestrictedFileField(label='Ballot order file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    result_forms_file =\
        RestrictedFileField(label='Result forms file',
                            required=True,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS,
                            check_file_size=False)
    tally_id = forms.IntegerField(widget=forms.HiddenInput())
