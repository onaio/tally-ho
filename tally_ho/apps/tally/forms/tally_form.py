from django import forms

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control required'
}


class TallyForm(forms.ModelForm):
    class Meta:
        model = Tally
        fields = ['name']

    administrators = forms.ModelMultipleChoiceField(queryset=UserProfile.objects.filter(groups__name__exact=groups.SUPER_ADMINISTRATOR),
                                                    widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(TallyForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class' : 'form-control'})

        if 'instance' in kwargs and kwargs['instance']:
            initial = kwargs.setdefault('initial', {})
            initial['administrators'] = [admin.pk for admin in kwargs['instance'].administrators.all()]

    def save(self):
        instance = forms.ModelForm.save(self)

        instance.administrators.clear()
        for admin in self.cleaned_data['administrators']:
            instance.administrators.add(admin)

        return instance
