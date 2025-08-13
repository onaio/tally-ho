import pathlib

from django import forms
from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _


class RestrictedFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        self.allowed_extensions = kwargs.pop('allowed_extensions', None)
        self.check_file_size = kwargs.pop('check_file_size', True)
        self.max_upload_size = kwargs.pop('max_upload_size', None)

        if self.check_file_size and not self.max_upload_size:
            self.max_upload_size = settings.MAX_FILE_UPLOAD_SIZE

        if not self.allowed_extensions:
            self.allowed_extensions = ['.png', '.jpg', '.doc', '.pdf']

        super(RestrictedFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(RestrictedFileField, self).clean(*args, **kwargs)
        if data:
            file_extension = pathlib.Path(data.name).suffix

            try:
                if file_extension in self.allowed_extensions:
                    if self.check_file_size and\
                            data.size > self.max_upload_size:
                        raise forms.ValidationError(
                            _('File size must be under'
                              f' {filesizeformat(self.max_upload_size)}.'
                              ' Current file size is'
                              f' {filesizeformat(data.size)}.'))
                else:
                    allowed_extensions = ', '.join(self.allowed_extensions)
                    raise forms.ValidationError(
                        _(f'File extension ({file_extension})'
                          ' is not supported.'
                          f' Allowed extension(s) are: {allowed_extensions}.'))
            except AttributeError:
                pass

            return data
