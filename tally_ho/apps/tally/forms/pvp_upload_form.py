from django import forms
from django.utils.translation import gettext_lazy as _


class PvpUploadForm(forms.Form):
    """One file input — the PVP results bundle (zip)."""

    zip_file = forms.FileField(
        label=_("PVP bundle (.zip)"),
        widget=forms.ClearableFileInput(
            attrs={"accept": ".zip,application/zip"},
        ),
    )
