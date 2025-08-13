from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.forms.fields import RestrictedFileField
from tally_ho.apps.tally.models.comment import Comment
from tally_ho.apps.tally.models.electrol_race import ElectrolRace


class EditElectrolRaceForm(ModelForm):
    class Meta:
        model = ElectrolRace
        fields = localized_fields = [
            'election_level',
            'ballot_name',
            'active',
            'disable_reason',
            'tally',
            'background_image',
        ]

    background_image = RestrictedFileField(required=False)

    tally_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    comment_input = forms.CharField(
        required=False,
        label=_("Add new comments"),
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 5}),
    )

    def __init__(self, *args, **kwargs):
        super(EditElectrolRaceForm, self).__init__(*args, **kwargs)
        if self.instance.active:
            self.fields.pop('disable_reason')

    def save(self):
        if self.is_valid():
            tally_id = self.cleaned_data.get('tally_id')
            electrol_race = super(EditElectrolRaceForm, self).save()
            comment = self.cleaned_data.get('comment_input')

            if comment:
                Comment(text=comment,
                        electrol_race=electrol_race,
                        tally_id=tally_id).save()
            return electrol_race
