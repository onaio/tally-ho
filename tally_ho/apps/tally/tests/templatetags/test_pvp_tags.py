from django.template import Context, Template

from tally_ho.apps.tally.models.pvp_submission import PvpSubmission
from tally_ho.apps.tally.models.pvp_upload_bundle import PvpUploadBundle
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.tests.test_base import (
    TestBase, create_ballot, create_center, create_electrol_race,
    create_result_form, create_station, create_tally,
)


class TestPvpBadgeTag(TestBase):
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

    def _render(self, result_form):
        tpl = Template("{% load pvp_tags %}{% pvp_badge rf %}")
        return tpl.render(Context({"rf": result_form})).strip()

    def test_renders_nothing_for_non_pvp_form(self):
        rf = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=3, form_state=FormState.UNSUBMITTED,
        )
        self.assertEqual(self._render(rf), "")

    def test_renders_badge_for_pvp_sourced_form(self):
        rf = create_result_form(
            tally=self.tally, ballot=self.ballot, center=self.center,
            station_number=3, form_state=FormState.DATA_ENTRY_2,
        )
        bundle = PvpUploadBundle.objects.create(
            tally=self.tally, uploaded_by=self.user, filename="b.zip",
        )
        sub = PvpSubmission.objects.create(
            tally=self.tally, bundle=bundle,
            odk_instance_id="uuid:1", odk_form_id="results_x",
            barcode=rf.barcode,
        )
        rf.pvp_submission = sub
        rf.save()
        body = self._render(rf)
        self.assertIn("PVP", body)
        self.assertIn("pvp-badge", body)
        self.assertIn("Populated from PVP", body)
