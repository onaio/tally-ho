import os
import shutil

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import pre_save

from tally_ho.apps.tally.models.ballot import (
    Ballot,
    auto_delete_document,
    document_name,
)
from tally_ho.libs.tests.test_base import TestBase, create_ballot, create_tally


class TestBallot(TestBase):
    def setUp(self):
        self._create_and_login_user()

    def test_document_name_function(self):
        document_path = "ballot_1/image.png"
        self.assertEqual("image.png", document_name(document_path))

    def test_auto_delete_document_function(self):
        pre_save.disconnect(sender=Ballot, dispatch_uid="ballot_update")
        file_size = settings.MAX_FILE_UPLOAD_SIZE
        pdf_file_name = "file.pdf"
        image_file_name = "image.jpg"
        pdf_file = SimpleUploadedFile(
            pdf_file_name, bytes(file_size), content_type="application/pdf")
        image_file = SimpleUploadedFile(
            image_file_name, bytes(file_size), content_type="image/jpeg")
        tally = create_tally()
        ballot = create_ballot(tally=tally, document=pdf_file)

        self.assertIn(pdf_file_name, ballot.document.path)
        ballot_instance = Ballot.objects.get(pk=ballot.pk)
        ballot_instance.document = image_file
        auto_delete_document(Ballot, ballot_instance)
        ballot_instance.save()
        ballot.refresh_from_db()
        self.assertNotIn(pdf_file_name, ballot.document.path)
        self.assertIn(image_file_name, ballot.document.path)
        shutil.rmtree(os.path.dirname(ballot.document.path))
        pdf_file.close()
        image_file.close()
