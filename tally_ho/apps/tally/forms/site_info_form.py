
from django.forms import (
    ModelForm,
    TextInput
)
from django.conf import settings
from django.contrib.sites.models import Site

from tally_ho.apps.tally.models.site_info import SiteInfo


class SiteInfoForm(ModelForm):
    class Meta:
        model = SiteInfo
        fields = ['user_idle_timeout']

        widgets = {
            'user_idle_timeout': TextInput(attrs={'size': 50})
        }

    def __init__(self, *args, **kwargs):
        super(SiteInfoForm, self).__init__(*args, **kwargs)

    def clean(self):
        if self.is_valid():
            cleaned_data = super(SiteInfoForm, self).clean()

            return cleaned_data

    def save(self):
        if self.is_valid():
            user_idle_timeout = self.cleaned_data.get('user_idle_timeout')
            site_id = getattr(settings, "SITE_ID", None)
            site_info = None
            site = Site.objects.get(pk=site_id)

            try:
                site_info = SiteInfo.objects.get(site=site)
                site_info.user_idle_timeout = user_idle_timeout
                site_info.save()
            except SiteInfo.DoesNotExist:
                site_info = SiteInfo.objects.create(
                    site=site, user_idle_timeout=user_idle_timeout)

            return site_info
