from tally_ho.apps.tally.forms.tally_form import TallyForm
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import TestBase, create_tally


class TestTallyForm(TestBase):
    def setUp(self):
        self._create_permission_groups()
        self._create_and_login_user(username="admin", password="pass")
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def _form_data(self, **overrides):
        data = {
            "name": "atally",
            "administrators": [self.user.pk],
            "print_cover_in_intake": True,
            "print_cover_in_clearance": True,
            "print_cover_in_quality_control": True,
            "print_cover_in_audit": True,
            "pvp_mode": PvpMode.DISABLED.value,
        }
        data.update(overrides)
        return data

    def test_pvp_mode_field_present(self):
        form = TallyForm()
        self.assertIn("pvp_mode", form.fields)

    def test_pvp_mode_de1_and_de2_option_is_disabled_in_widget(self):
        form = TallyForm()
        rendered = str(form["pvp_mode"])
        expected = f'value="{PvpMode.DE1_AND_DE2.value}" disabled'
        self.assertIn(expected, rendered)

    def test_pvp_mode_de1_and_de2_rejected_server_side(self):
        form = TallyForm(data=self._form_data(
            pvp_mode=PvpMode.DE1_AND_DE2.value,
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("pvp_mode", form.errors)

    def test_pvp_mode_de1_only_accepted(self):
        form = TallyForm(data=self._form_data(
            pvp_mode=PvpMode.DE1_ONLY.value,
        ))
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_pvp_mode_disabled_accepted(self):
        form = TallyForm(data=self._form_data(
            pvp_mode=PvpMode.DISABLED.value,
        ))
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_pvp_mode_round_trip_via_form_save(self):
        tally = create_tally()
        form = TallyForm(
            instance=tally,
            data=self._form_data(
                name=tally.name, pvp_mode=PvpMode.DE1_ONLY.value,
            ),
        )
        self.assertTrue(form.is_valid(), msg=form.errors)
        form.save()
        tally.refresh_from_db()
        self.assertEqual(tally.pvp_mode, PvpMode.DE1_ONLY)
