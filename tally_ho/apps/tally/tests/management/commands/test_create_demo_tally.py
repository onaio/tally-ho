from django.test import TestCase

from tally_ho.apps.tally.management.commands.create_demo_tally import (
    create_demo_tally,
)
from tally_ho.apps.tally.management.commands.create_demo_users import (
    create_demo_users_with_groups,
)
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.pvp_mode import PvpMode


class TestCreateDemoTally(TestCase):
    name = "Demo Tally"

    def test_seeds_full_hierarchy(self):
        tally = create_demo_tally(name=self.name)

        self.assertEqual(tally.name, self.name)
        self.assertEqual(tally.pvp_mode, PvpMode.DISABLED)
        self.assertEqual(ElectrolRace.objects.filter(tally=tally).count(), 2)
        self.assertEqual(Ballot.objects.filter(tally=tally).count(), 2)
        self.assertEqual(Candidate.objects.filter(tally=tally).count(), 6)
        self.assertEqual(Center.objects.filter(tally=tally).count(), 2)
        self.assertEqual(Station.objects.filter(tally=tally).count(), 4)
        self.assertEqual(ResultForm.objects.filter(tally=tally).count(), 8)

    def test_result_forms_use_deterministic_barcodes(self):
        tally = create_demo_tally(name=self.name)

        barcodes = sorted(
            ResultForm.objects.filter(tally=tally).values_list(
                "barcode", flat=True,
            ),
        )
        self.assertEqual(
            barcodes,
            [str(10000001 + i) for i in range(8)],
        )

    def test_result_forms_start_unsubmitted(self):
        tally = create_demo_tally(name=self.name)

        states = set(
            ResultForm.objects.filter(tally=tally).values_list(
                "form_state", flat=True,
            ),
        )
        self.assertEqual(states, {FormState.UNSUBMITTED})

    def test_candidate_ids_are_numeric_and_per_ballot(self):
        tally = create_demo_tally(name=self.name)

        for ballot in Ballot.objects.filter(tally=tally):
            ids = sorted(
                ballot.candidates.values_list("candidate_id", flat=True),
            )
            self.assertEqual(ids, [1, 2, 3])

    def test_is_idempotent(self):
        first = create_demo_tally(name=self.name)
        second = create_demo_tally(name=self.name)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Tally.objects.filter(name=self.name).count(), 1)
        self.assertEqual(
            ResultForm.objects.filter(tally=first).count(), 8,
        )

    def test_clean_wipes_existing_tally(self):
        first = create_demo_tally(name=self.name)
        first_pk = first.pk

        second = create_demo_tally(name=self.name, clean=True)

        self.assertNotEqual(first_pk, second.pk)
        self.assertEqual(Tally.objects.filter(name=self.name).count(), 1)
        self.assertFalse(
            ResultForm.objects.filter(tally_id=first_pk).exists(),
        )

    def test_stations_have_registrants_for_recon(self):
        tally = create_demo_tally(name=self.name)

        for station in Station.objects.filter(tally=tally):
            self.assertIsNotNone(station.registrants)
            self.assertGreater(station.registrants, 0)

    def test_super_admin_demo_user_can_access_tally(self):
        create_demo_users_with_groups()

        tally = create_demo_tally(name=self.name)

        profile = UserProfile.objects.get(username="super_administrator")
        self.assertTrue(
            profile.administrated_tallies.filter(id=tally.id).exists(),
        )
