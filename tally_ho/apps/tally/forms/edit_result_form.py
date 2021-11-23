from django import forms

from django.forms import (
    ModelForm,
    ValidationError,
    ModelChoiceField
)
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models import ResultForm
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.ballot import Ballot


class EditResultForm(ModelForm):
    class Meta:
        model = ResultForm
        fields = localized_fields = ['ballot',
                                     'center',
                                     'office',
                                     'gender',
                                     'tally']

        widgets = {"tally": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super(EditResultForm, self).__init__(*args, **kwargs)

        if self.initial.get('tally'):
            self.fields['center'] = ModelChoiceField(
                queryset=Center.objects.filter(
                    tally__id=self.initial['tally']))
            self.fields['office'] = ModelChoiceField(
                queryset=Office.objects.filter(
                    tally__id=self.initial['tally']))
            self.fields['ballot'] = ModelChoiceField(
                queryset=Ballot.objects.filter(
                    tally__id=self.initial['tally']))
        self.fields['gender'].choices = self.fields['gender'].choices[:-1]

    def clean(self):
        cleaned_data = super(EditResultForm, self).clean()
        center = cleaned_data.get('center', None)
        ballot = cleaned_data.get('ballot', None)

        if ballot and not ballot.active:
            raise ValidationError(_('Race for ballot is disabled'))

        if center and not center.active:
            raise ValidationError(_('Selected center is disabled'))

        if center.sub_constituency and \
                ballot.number != center.sub_constituency.code:
            raise ValidationError(
                _('Ballot number do not match for center and station'))

        return cleaned_data
