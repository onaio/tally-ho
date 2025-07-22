from django import forms
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.form import lower_case_form_data

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
        fields = [
            'name',
            'print_cover_in_intake',
            'print_cover_in_clearance',
            'print_cover_in_quality_control',
            'print_cover_in_audit'
        ]

    administrators = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.filter(
            groups__name__exact=groups.SUPER_ADMINISTRATOR),
        widget=forms.CheckboxSelectMultiple(),
        label=_('Administrators'),)

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance']:
            initial = kwargs.setdefault('initial', {})
            initial['administrators'] = [
                admin.pk for admin in kwargs['instance'].administrators.all()]

        super(TallyForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class_': 'form-control'})

        self.fields['print_cover_in_intake'].label =\
            _('Enable Cover Printing in Intake')
        self.fields['print_cover_in_clearance'].label =\
            _('Enable Cover Printing in Clearance')
        self.fields['print_cover_in_quality_control'].label =\
            _('Enable Cover Printing in Quality Control')
        self.fields['print_cover_in_audit'].label =\
            _('Enable Cover Printing in Audit')

    def clean(self):
        if self.is_valid():
            lower_case_form_data(self, TallyForm, ['name'])

    def save(self):
        instance = forms.ModelForm.save(self)

        instance.administrators.clear()
        for admin in self.cleaned_data['administrators']:
            instance.administrators.add(admin)

        return instance
