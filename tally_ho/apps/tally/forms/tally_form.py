from django import forms

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.user_profile import UserProfile


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control required'
}


class TallyForm(forms.Form):
    super_admin_users = tuple((user.id, "%s - %s %s" % (user.username, user.first_name, user.last_name))
                        for user in UserProfile.objects.filter(groups__name__exact=groups.SUPER_ADMINISTRATOR))

    name = forms.CharField(label='Tally name', required=True)
    subconst_file = forms.FileField(label='Subconstituency file', required=True)
    centers_file = forms.FileField(label='Centers file', required=True)
    stations_file = forms.FileField(label='Stations file', required=True)
    candidates_file = forms.FileField(label='Candidates file', required=True)
    ballots_order_file = forms.FileField(label='Ballot order file', required=True)
    result_forms_file = forms.FileField(label='Result forms file', required=True)

    administrators = forms.MultipleChoiceField(label='Select administrators',
                    widget=forms.CheckboxSelectMultiple(),
                    choices=super_admin_users)

    def __init__(self, *args, **kargs):
        super(TallyForm, self).__init__(*args, **kargs)
        self.fields['name'].widget.attrs.update({'class' : 'form-control'})

