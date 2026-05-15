"""Seed a minimal but realistic tally for dogfooding the PVP upload flow.

Builds a single tally with 2 ballots, 6 candidates, 2 centers, 4 stations,
and 8 result forms in ``UNSUBMITTED``. Re-running is idempotent on name;
``--clean`` wipes the existing tally with the same name first.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import gettext_lazy

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.models.enums.pvp_mode import PvpMode
from tally_ho.libs.models.enums.race_type import RaceType
from tally_ho.libs.verify.quarantine_checks import (
    create_quarantine_checks as ensure_quarantine_checks,
)


DEFAULT_NAME = "Demo Tally"
BARCODE_START = 10000001
STATION_REGISTRANTS = 200

BALLOTS = (
    {
        "number": 1,
        "election_level": "Presidential",
        "race_type": RaceType.PRESIDENTIAL,
    },
    {
        "number": 2,
        "election_level": "Parliamentary",
        "race_type": RaceType.GENERAL,
    },
)
CENTER_CODES = (1001, 1002)
STATION_GENDERS = ((1, Gender.MALE), (2, Gender.FEMALE))


def create_demo_tally(name=DEFAULT_NAME, clean=False):
    """Idempotently create the demo tally and return it."""
    with transaction.atomic():
        if clean:
            _delete_tally_cascade(name)

        tally, _ = Tally.objects.get_or_create(
            name=name,
            defaults={"pvp_mode": PvpMode.DISABLED},
        )

        region, _ = Region.objects.get_or_create(
            name="Demo Region", tally=tally,
        )
        office, _ = Office.objects.get_or_create(
            name="Demo Office", tally=tally, region=region,
            defaults={"number": 1},
        )
        constituency, _ = Constituency.objects.get_or_create(
            name="Demo Constituency", tally=tally,
        )
        sub_con, _ = SubConstituency.objects.get_or_create(
            code=1, tally=tally,
            defaults={
                "name": "Demo SubCon",
                "constituency": constituency,
                "number_of_ballots": len(BALLOTS),
            },
        )

        ballots_by_number = _create_ballots_and_candidates(tally)
        centers = _create_centers_and_stations(tally, office, sub_con)
        _create_result_forms(tally, office, ballots_by_number, centers)
        ensure_quarantine_checks(tally_id=tally.id)

        return tally


def _delete_tally_cascade(name):
    # Most FKs are on_delete=PROTECT, so we have to walk the hierarchy
    # bottom-up before deleting the Tally row itself.
    for tally in Tally.objects.filter(name=name):
        QuarantineCheck.objects.filter(tally=tally).delete()
        ResultForm.objects.filter(tally=tally).delete()
        Candidate.objects.filter(tally=tally).delete()
        Station.objects.filter(tally=tally).delete()
        Center.objects.filter(tally=tally).delete()
        SubConstituency.objects.filter(tally=tally).delete()
        Constituency.objects.filter(tally=tally).delete()
        Ballot.objects.filter(tally=tally).delete()
        ElectrolRace.objects.filter(tally=tally).delete()
        Office.objects.filter(tally=tally).delete()
        Region.objects.filter(tally=tally).delete()
        tally.delete()


def _create_ballots_and_candidates(tally):
    ballots_by_number = {}
    for spec in BALLOTS:
        race, _ = ElectrolRace.objects.get_or_create(
            tally=tally,
            election_level=spec["election_level"],
            ballot_name=f"Ballot {spec['number']}",
        )
        ballot, _ = Ballot.objects.get_or_create(
            tally=tally,
            number=spec["number"],
            electrol_race=race,
            defaults={"race_type": spec["race_type"]},
        )
        ballots_by_number[spec["number"]] = ballot
        for candidate_id in (1, 2, 3):
            Candidate.objects.get_or_create(
                tally=tally,
                ballot=ballot,
                candidate_id=candidate_id,
                defaults={
                    "electrol_race": race,
                    "full_name": (
                        f"Candidate {candidate_id} "
                        f"(Ballot {spec['number']})"
                    ),
                    "order": candidate_id,
                    "race_type": spec["race_type"],
                },
            )
    return ballots_by_number


def _create_centers_and_stations(tally, office, sub_con):
    centers = []
    for code in CENTER_CODES:
        center, _ = Center.objects.get_or_create(
            tally=tally,
            code=code,
            defaults={
                "name": f"Demo Center {code}",
                "office": office,
                "sub_constituency": sub_con,
            },
        )
        centers.append(center)
        for station_number, gender in STATION_GENDERS:
            Station.objects.get_or_create(
                tally=tally,
                center=center,
                station_number=station_number,
                defaults={
                    "gender": gender,
                    "sub_constituency": sub_con,
                    "registrants": STATION_REGISTRANTS,
                },
            )
    return centers


def _create_result_forms(tally, office, ballots_by_number, centers):
    barcode = BARCODE_START
    for center in centers:
        for station_number, gender in STATION_GENDERS:
            for ballot_number, ballot in sorted(ballots_by_number.items()):
                ResultForm.objects.get_or_create(
                    tally=tally,
                    barcode=str(barcode),
                    defaults={
                        "ballot": ballot,
                        "center": center,
                        "office": office,
                        "station_number": station_number,
                        "gender": gender,
                        "form_state": FormState.UNSUBMITTED,
                        "serial_number": barcode,
                    },
                )
                barcode += 1


class Command(BaseCommand):
    help = gettext_lazy(
        "Seed a demo tally with centers, stations, ballots, candidates, and "
        "result forms for dogfooding the PVP upload flow."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            default=DEFAULT_NAME,
            help="Tally name (used as the idempotency key).",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete any existing tally with the same name first.",
        )

    def handle(self, *args, **options):
        tally = create_demo_tally(
            name=options["name"], clean=options["clean"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo tally ready: id={tally.id}, name={tally.name!r}, "
                f"result_forms={tally.result_forms.count()}"
            )
        )
