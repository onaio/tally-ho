from django import forms
from django.forms.formsets import BaseFormSet
from django.utils.translation import ugettext as _


class BaseCandidateFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return

        try:
            [form.cleaned_data['votes'] for form in self.forms]
        except KeyError:
            raise forms.ValidationError(_('Missing votes for candidate'))
