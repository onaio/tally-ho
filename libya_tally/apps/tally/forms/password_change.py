from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import ugettext_lazy as _


class PasswordChangeForm(PasswordChangeForm):

    new_password1 = forms.CharField(
        min_length=6, label=_("New password"), widget=forms.PasswordInput)

    new_password2 = forms.CharField(
        label=_("New password confirmation"), widget=forms.PasswordInput)

    def save(self, commit=True):
        """
        Saves the new password and set user_profile reset_password to false
        """
        self.user.set_password(self.cleaned_data["new_password1"])
        if commit:
            self.user.save()
            profile = self.user.userprofile
            profile.reset_password = False
            profile.save()

        return self.user
