from django import forms
from tally_ho.apps.tally.forms.fields import RestrictedFileField

ALLOWED_FILE_EXTENTIONS = ['.csv']


class TallyFilesForm(forms.Form):
    subconst_file =\
        RestrictedFileField(label='Subconstituency file',
                            required=True,
                            check_file_size=False,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    centers_file =\
        RestrictedFileField(label='Centers file',
                            required=True,
                            check_file_size=False,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    stations_file =\
        RestrictedFileField(label='Stations file',
                            required=True,
                            check_file_size=False,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    candidates_file =\
        RestrictedFileField(label='Candidates file',
                            required=True,
                            check_file_size=False,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    ballots_order_file =\
        RestrictedFileField(label='Ballot order file',
                            required=True,
                            check_file_size=False,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
    result_forms_file =\
        RestrictedFileField(label='Result forms file',
                            required=True,
                            check_file_size=False,
                            allowed_extensions=ALLOWED_FILE_EXTENTIONS)
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
                    _(f'File extension ({file_extension}) is not supported.'
                      ' Allowed extensions are .csv'))
