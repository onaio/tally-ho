import pathlib

from django import forms
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django.conf import settings


class RestrictedFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        self.allowed_extensions = kwargs.pop('allowed_extensions', None)
        self.max_upload_size = kwargs.pop('max_upload_size', None)

        if not self.max_upload_size:
            self.max_upload_size = settings.MAX_FILE_UPLOAD_SIZE

        if not self.allowed_extensions:
            self.allowed_extensions = ['png', 'jpg', 'doc', 'pdf']

        super(RestrictedFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(RestrictedFileField, self).clean(*args, **kwargs)
        if data:
            file_extension = pathlib.Path(data.name).suffix

            try:
                if file_extension in self.allowed_extensions:
                    if data.size > self.max_upload_size:
                        raise forms.ValidationError(
                            _(u'File extention (%s) is not supported.'
                                ' Allowed extensions are: %s.') %
                            (filesizeformat(self.max_upload_size),
                                filesizeformat(data.size)))
                else:
                    raise forms.ValidationError(
                        _(u'File size must be under %s.'
                            ' Current file size is %s.') %
                        (file_extension, ', '.join(self.allowed_extensions)))
            except AttributeError:
                pass

            return data
        pass
