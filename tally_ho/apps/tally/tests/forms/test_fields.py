from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.forms import ValidationError
from django.test import SimpleTestCase

from tally_ho.apps.tally.forms.fields import RestrictedFileField


class RestrictedFileFieldTest(SimpleTestCase):

    def test_file_extension_error(self):
        f = RestrictedFileField()
        file_size = settings.MAX_FILE_UPLOAD_SIZE
        video = SimpleUploadedFile(
            "file.mp4", bytes(file_size), content_type="video/mp4")
        file_extension_error =\
            str('File extention (.mp4) is not supported.'
                ' Allowed extensions are: .png, .jpg, .doc, .pdf.')
        with self.assertRaisesMessage(ValidationError, file_extension_error):
            f.clean(video)

    def test_file_size_error(self):
        f = RestrictedFileField()
        file_size = settings.MAX_FILE_UPLOAD_SIZE * 2
        image = SimpleUploadedFile(
            "image.jpg", bytes(file_size), content_type="image/jpeg")
        file_size_error =\
            str('File size must be under 10.0\\xa0MB.'
                ' Current file size is 20.0\\xa0MB.')
        with self.assertRaisesMessage(ValidationError, file_size_error):
            f.clean(image)

    def test_no_validation_error(self):
        f = RestrictedFileField()
        file_size = settings.MAX_FILE_UPLOAD_SIZE
        image = SimpleUploadedFile(
            "image.jpg", bytes(file_size), content_type="image/jpeg")
        self.assertEqual(image, f.clean(image))

    def test_required_false_raises_no_error(self):
        f = RestrictedFileField(required=False)
        self.assertEqual(None, f.clean(''))
