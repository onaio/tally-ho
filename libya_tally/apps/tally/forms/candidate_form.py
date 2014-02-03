from django import forms


class CandidateForm(forms.Form):
    votes = forms.IntegerField(min_value=0, required=True)
