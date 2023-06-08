from django import forms
from django.forms import ModelChoiceField, ModelForm
from tally_ho.apps.tally.forms.fields import RestrictedFileField
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.comment import Comment
from tally_ho.apps.tally.models.electrol_race import ElectrolRace


class EditBallotForm(ModelForm):
    class Meta:
        model = Ballot
        fields = localized_fields = [
            'number',
            'electrol_race',
            'active',
            'disable_reason',
            'available_for_release',
            'document',
        ]

    document = RestrictedFileField(required=False)

    comment_input = forms.CharField(
        required=False,
        label=_("Add new comments"),
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 5}),
    )

    tally_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super(EditBallotForm, self).__init__(*args, **kwargs)
        tally_id = self.initial.get('tally_id')
        self.fields['electrol_race'] = ModelChoiceField(
                queryset=ElectrolRace.objects.filter(tally__id=tally_id))

        if self.instance.active:
            self.fields.pop('disable_reason')

    def save(self):
        if self.is_valid():
            tally_id = self.cleaned_data.get('tally_id')
            ballot_number = self.cleaned_data.get('number')
            ballot = None
            try:
                ballot = Ballot.objects.get(number=ballot_number,
                                            tally__id=tally_id)
            except Ballot.DoesNotExist:
                raise forms.ValidationError(_('Ballot does not exist'))
            else:
                tally_id = self.cleaned_data.get('tally_id')
                comment = self.cleaned_data.get('comment_input')

                if comment:
                    Comment(text=comment,
                            ballot=ballot,
                            tally_id=tally_id).save()

            return super(EditBallotForm, self).save()
