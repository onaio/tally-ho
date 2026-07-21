import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.test import override_settings

from tally_ho.apps.tally.models.result_form_image import ResultFormImage
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.result_form_image_kind import (
    ResultFormImageKind,
)
from tally_ho.libs.models.enums.result_form_image_source import (
    ResultFormImageSource,
)
from tally_ho.libs.tests.test_base import (
    TestBase, create_ballot, create_center, create_electrol_race,
    create_result_form, create_station, create_tally,
)


class TestResultFormImagesTag(TestBase):
    def setUp(self):
        self._create_and_login_user()
        self.tally = create_tally()
        electrol_race = create_electrol_race(
            self.tally, election_level="presidential",
            ballot_name="Presidential",
        )
        self.ballot = create_ballot(
            self.tally, electrol_race=electrol_race, number=1,
        )
        self.center = create_center(tally=self.tally)
        self.station = create_station(
            center=self.center, tally=self.tally,
            station_number=3, registrants=300,
        )
        self.result_form = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=3, form_state=FormState.DATA_ENTRY_2,
        )
        self._media_root = tempfile.mkdtemp(prefix="tally_test_media_")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)

    def _add_image(self, **overrides):
        defaults = {
            "tally": self.tally,
            "result_form": self.result_form,
            "image": SimpleUploadedFile(
                "photo.jpg", b"jpg-bytes", content_type="image/jpeg",
            ),
        }
        defaults.update(overrides)
        return ResultFormImage.objects.create(**defaults)

    def _render(self):
        tpl = Template(
            "{% load result_form_tags %}{% result_form_images rf %}"
        )
        return tpl.render(Context({"rf": self.result_form})).strip()

    def test_renders_nothing_when_no_images(self):
        self.assertEqual(self._render(), "")

    def test_renders_thumbnails_for_each_image(self):
        self._add_image(kind=ResultFormImageKind.CLERK_SIGNATURE)
        self._add_image(kind=ResultFormImageKind.FORM_PAGE_1)
        body = self._render()
        self.assertEqual(body.count("<img"), 2)

    def test_shows_caption_and_pvp_source(self):
        self._add_image(
            source=ResultFormImageSource.PVP_IMPORT,
            kind=ResultFormImageKind.CLERK_SIGNATURE,
            caption="signed page",
        )
        body = self._render()
        self.assertIn("signed page", body)
        self.assertIn("PVP", body)
