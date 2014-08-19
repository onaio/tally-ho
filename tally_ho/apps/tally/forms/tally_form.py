from django import forms


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control required'
}

def content_file_name(instance, filename):
        return '/'.join(['data/uploaded', instance.user.username, filename])

class TallyForm(forms.Form):
    name = forms.CharField(label='Tally name', required=True)
    subconst_file = forms.FileField(label='Subconstituency file', required=True)
    centers_file = forms.FileField(label='Centers file', required=True)
    #stations_file = forms.FileField(label='Stations file', required=True)
    #candidates_file = forms.FileField(label='Candidates file', required=True)
    #ballots_order_file = forms.FileField(label='Ballot order file', required=True)
    #result_forms_file = forms.FileField(label='Result forms file', required=True)

    def __init__(self, *args, **kargs):
        super(TallyForm, self).__init__(*args, **kargs)
        self.fields['name'].widget.attrs.update({'class' : 'form-control'})

