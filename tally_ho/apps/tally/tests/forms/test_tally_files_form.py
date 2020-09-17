from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from tally_ho.apps.tally.forms.tally_files_form import TallyFilesForm


class TallyFilesFormTest(TestCase):
    data_dict = {'tally_id': 1}
    csv_file = SimpleUploadedFile(
        "file.csv",
        b'content',
        content_type="text/csv")
    image_file = SimpleUploadedFile(
        "image.jpg",
        b'content',
        content_type="image/jpeg")

    def test_file_extension_error(self):
        file_dict = {
            'subconst_file': self.image_file,
            'centers_file': self.csv_file,
            'stations_file': self.csv_file,
            'candidates_file': self.csv_file,
            'ballots_order_file': self.csv_file,
            'result_forms_file': self.csv_file
        }
        form = TallyFilesForm(data=self.data_dict, files=file_dict)
        self.assertFalse(form.is_valid())
        self.assertIn(
            str('File extension (.jpg) is not supported.'
                ' Allowed extension(s) are: .csv.'),
            form.errors['subconst_file'])

    def test_correct_file_extension(self):
        file_dict = {
            'subconst_file': self.csv_file,
            'centers_file': self.csv_file,
            'stations_file': self.csv_file,
            'candidates_file': self.csv_file,
            'ballots_order_file': self.csv_file,
            'result_forms_file': self.csv_file
        }
        form = TallyFilesForm(data=self.data_dict, files=file_dict)
        self.assertTrue(form.is_valid())
