from django.contrib.auth.models import Group
from django.forms import ModelForm, TextInput, Select, PasswordInput, \
        ModelChoiceField, SelectMultiple, RadioSelect, HiddenInput

from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.permissions import groups

disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class EditUserProfileForm(ModelForm):
    MANDATORY_FIELDS = ['username', 'group']

    class Meta:
        model = UserProfile
        fields = localized_fields = ['username',
                                     'first_name',
                                     'last_name',
                                     'email',
                                     #'groups',
                                     'tally',
                                     ]

        widgets = {
            'username': TextInput(attrs={'size': 50}),
            'first_name': TextInput(attrs={'size': 50}),
            'last_name': TextInput(attrs={'size': 50}),
            'email': TextInput(attrs={'size': 50}),
            #'groups': Select(attrs={'class': 'selector'})
        }

    qs = Group.objects.exclude(name__in=[groups.SUPER_ADMINISTRATOR, groups.TALLY_MANAGER])
    group = ModelChoiceField(queryset=qs, required=True)

    def __init__(self, *args, **kwargs):

        if 'instance' in kwargs and kwargs['instance']:
            initial = kwargs.setdefault('initial', {})
            initial['group'] = kwargs['instance'].groups.first()

        super(EditUserProfileForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            if key not in self.MANDATORY_FIELDS:
                self.fields[key].required = False

        if self.initial.get('tally_id'):
            self.fields['tally'].initial = self.initial.get('tally_id')
            self.fields['tally'].widget = HiddenInput()

    def save(self):
        user = super(EditUserProfileForm, self).save()
        group = self.cleaned_data.get('group')

        user.groups.clear()
        user.groups.add(group)

        if self.initial.get('tally_id'):
            tally = Tally.objects.get(id=self.initial.get('tally_id'))
            user.tally = tally
            user.save()

        if not user.password:
            user.set_password(user.username)
            user.reset_password = True
            user.save()

        return user


class EditAdminProfileForm(ModelForm):
    MANDATORY_FIELDS = ['username']

    class Meta:
        model = UserProfile
        fields = localized_fields = ['username',
                                     'first_name',
                                     'last_name',
                                     'email',
                                     'administrated_tallies',
                                     ]

        widgets = {
            'username': TextInput(attrs={'size': 50}),
            'first_name': TextInput(attrs={'size': 50}),
            'last_name': TextInput(attrs={'size': 50}),
            'email': TextInput(attrs={'size': 50}),
        }

    def __init__(self, *args, **kwargs):
        super(EditAdminProfileForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            if key not in self.MANDATORY_FIELDS:
                self.fields[key].required = False

    def save(self):
        user = super(EditAdminProfileForm, self).save()

        super_admin = Group.objects.get(name=groups.SUPER_ADMINISTRATOR)
        user.groups.add(super_admin)

        if not user.password:
            user.set_password(user.username)
            user.reset_password = True

        user.save()
