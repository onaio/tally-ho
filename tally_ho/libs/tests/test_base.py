from django.contrib.auth.models import AnonymousUser, Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.utils import timezone

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.clearance import Clearance
from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.quality_control import QualityControl
from tally_ho.apps.tally.models.reconciliation_form import ReconciliationForm
from tally_ho.apps.tally.models.region import Region
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_stats import ResultFormStats
from tally_ho.apps.tally.models.site_info import SiteInfo
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.permissions.groups import (
    add_user_to_group,
    create_permission_groups,
)
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.verify.quarantine_checks import (
    create_quarantine_checks as create_quarantine_checks_fn,
)


def configure_messages(request):
    setattr(request, "session", "session")
    messages = FallbackStorage(request)
    setattr(request, "_messages", messages)


def create_audit(result_form, user, reviewed_team=False):
    return Audit.objects.create(
        user=user,
        reviewed_team=reviewed_team,
        result_form=result_form,
        action_prior_to_recommendation=1,
        resolution_recommendation=1,
    )


def create_ballot(
    tally,
    electrol_race=None,
    active=True,
    number=1,
    available_for_release=False,
    document="",
):
    if electrol_race is None:
        electrol_race_data = electrol_races[0]
        electrol_race = create_electrol_race(tally, **electrol_race_data)
    ballot, _ = Ballot.objects.get_or_create(
        active=active,
        number=number,
        tally=tally,
        available_for_release=available_for_release,
        electrol_race=electrol_race,
        document=document,
    )
    return ballot


def create_electrol_race(
    tally,
    election_level,
    ballot_name,
    active=True,
    disable_reason=None,
):
    electrol_race, _ = ElectrolRace.objects.get_or_create(
        tally=tally,
        election_level=election_level,
        ballot_name=ballot_name,
        active=active,
        disable_reason=disable_reason,
    )
    return electrol_race


def create_clearance(result_form, user, reviewed_team=False):
    date_team_modified = timezone.now() if reviewed_team else None

    return Clearance.objects.create(
        result_form=result_form,
        reviewed_team=reviewed_team,
        user=user,
        date_team_modified=date_team_modified,
    )


def create_result(result_form, candidate, user, votes):
    Result.objects.create(
        result_form=result_form,
        user=user,
        candidate=candidate,
        votes=votes,
        entry_version=EntryVersion.FINAL,
    )


def create_candidates(
    result_form,
    user,
    name="the candidate name",
    votes=123,
    women_name="women candidate name",
    num_results=10,
    tally=None,
):
    for i in range(num_results):
        candidate = Candidate.objects.create(
            ballot=result_form.ballot,
            candidate_id=1,
            full_name=name,
            order=0,
            tally=tally,
        )
        candidate_f = Candidate.objects.create(
            ballot=result_form.ballot,
            candidate_id=1,
            full_name=women_name,
            order=0,
            tally=tally,
        )
        create_result(result_form, candidate, user, votes)
        create_result(result_form, candidate_f, user, votes)


def create_candidate_result(
    result_form, user, name="the candidate name", votes=123, tally=None
):
    candidate = Candidate.objects.create(
        ballot=result_form.ballot,
        candidate_id=1,
        full_name=name,
        order=0,
        tally=tally,
    )
    create_result(result_form, candidate, user, votes)
    return candidate


def create_result_form(
    barcode="123456789",
    form_state=FormState.UNSUBMITTED,
    ballot=None,
    station_number=None,
    center=None,
    gender=Gender.MALE,
    force_ballot=True,
    name=None,
    serial_number=0,
    user=None,
    is_replacement=False,
    tally=None,
    office=None,
    electrol_race=None,
):
    if force_ballot and not ballot:
        ballot = create_ballot(tally, electrol_race=electrol_race)

    result_form, _ = ResultForm.objects.get_or_create(
        ballot=ballot,
        barcode=barcode,
        serial_number=serial_number,
        form_state=form_state,
        name=name,
        station_number=station_number,
        user=user,
        center=center,
        gender=gender,
        is_replacement=is_replacement,
        tally=tally,
        office=office,
    )

    return result_form


def create_tally(name="myTally"):
    tally, _ = Tally.objects.get_or_create(name=name)

    return tally


def center_data(code1, code2=None, station_number=1, tally_id=None):
    if not code2:
        code2 = code1

    return {
        "center_number": code1,
        "center_number_copy": code2,
        "station_number": station_number,
        "tally_id": tally_id,
        "station_number_copy": station_number,
    }


def create_candidate(ballot, candidate_name, tally=None):
    return Candidate.objects.create(
        ballot=ballot,
        full_name=candidate_name,
        candidate_id=1,
        order=1,
        tally=tally,
    )


def create_center(
    code="1",
    office_name="office",
    tally=None,
    active=True,
    sub_constituency=None,
    constituency=None,
):
    region = create_region(tally=tally)
    return Center.objects.get_or_create(
        code=code,
        mahalla="1",
        name="1",
        office=create_office(office_name, region=region),
        region="1",
        village="1",
        active=active,
        tally=tally,
        sub_constituency=sub_constituency,
        center_type=CenterType.GENERAL,
        constituency=constituency,
    )[0]


def create_office(name="office", tally=None, region=None):
    office, _ = Office.objects.get_or_create(
        name=name, tally=tally, region=region
    )

    return office


def create_reconciliation_form(
    result_form,
    user,
    entry_version=EntryVersion.FINAL,
    ballot_number_from=1,
    number_sorted_and_counted=1,
    number_of_voters=1,
    number_valid_votes=1,
    number_invalid_votes=1,
    number_of_voter_cards_in_the_ballot_box=1,
):
    return ReconciliationForm.objects.create(
        result_form=result_form,
        ballot_number_from=ballot_number_from,
        ballot_number_to=1,
        number_of_voters=number_of_voters,
        number_of_voter_cards_in_the_ballot_box=number_of_voter_cards_in_the_ballot_box,
        number_invalid_votes=number_invalid_votes,
        number_valid_votes=number_valid_votes,
        number_sorted_and_counted=number_sorted_and_counted,
        entry_version=entry_version,
        user=user,
    )


def create_quarantine_checks(quarantine_data):
    create_quarantine_checks_fn(quarantine_data=quarantine_data)


def create_recon_forms(result_form, user):
    recon1 = create_reconciliation_form(result_form, user)
    recon1.entry_version = EntryVersion.DATA_ENTRY_1
    recon1.save()

    recon2 = create_reconciliation_form(result_form, user)
    recon2.entry_version = EntryVersion.DATA_ENTRY_2
    recon2.save()


def create_quality_control(result_form, user):
    return QualityControl.objects.create(result_form=result_form, user=user)


def create_station(
    center,
    registrants=1,
    tally=None,
    active=True,
    station_number=1,
    gender=Gender.MALE,
):
    sc, _ = SubConstituency.objects.get_or_create(
        code=1, name="subConstituency", field_office="1"
    )

    station, _ = Station.objects.get_or_create(
        active=active,
        center=center,
        sub_constituency=sc,
        gender=gender,
        station_number=station_number,
        registrants=registrants,
        tally=tally,
    )
    return station


def create_result_form_stats(
    processing_time,
    user,
    result_form,
    approved_by_supervisor=False,
    reviewed_by_supervisor=False,
    data_entry_errors=0,
):
    result_form_stats, _ = ResultFormStats.objects.get_or_create(
        processing_time=processing_time,
        user=user,
        result_form=result_form,
        approved_by_supervisor=approved_by_supervisor,
        reviewed_by_supervisor=reviewed_by_supervisor,
        data_entry_errors=data_entry_errors,
    )

    return result_form_stats


def create_site_info(site, user_idle_timeout):
    site_info, _ = SiteInfo.objects.get_or_create(
        site=site, user_idle_timeout=user_idle_timeout
    )

    return site_info


def create_region(name="Region", tally=None):
    region, _ = Region.objects.get_or_create(
        name=name,
        tally=tally,
    )

    return region


def create_sub_constituency(
    code=1,
    tally=None,
    field_office="1",
    ballots=[],
    name="subConstituency",
):
    sub_constituency, _ = SubConstituency.objects.get_or_create(
        code=code, field_office=field_office, tally=tally, name=name
    )
    if len(ballots):
        sub_constituency.ballots.set(ballots)

    return sub_constituency


def create_constituency(name="Region", tally=None):
    constituency, _ = Constituency.objects.get_or_create(
        name=name,
        tally=tally,
    )

    return constituency


def result_form_data_blank(result_form):
    return {
        "result_form": result_form.pk,
        "tally_id": result_form.tally.pk,
        "form-TOTAL_FORMS": ["1"],
        "form-MAX_NUM_FORMS": ["1000"],
        "form-INITIAL_FORMS": ["0"],
        "form-0-votes": [""],
    }


def result_form_data(result_form):
    data = result_form_data_blank(result_form)
    data.update(
        {
            "number_of_voters": ["125"],
            "number_of_voter_cards_in_the_ballot_box": ["100"],
            "number_valid_votes": ["100"],
            "number_invalid_votes": ["25"],
            "number_sorted_and_counted": ["125"],
            "notes": [""],
            "form-TOTAL_FORMS": ["2"],
            "form-INITIAL_FORMS": ["0"],
            "form-MIN_NUM_FORMS": ["0"],
            "form-MAX_NUM_FORMS": ["1000"],
            "form-0-votes": ["4"],
            "form-1-votes": ["1"],
        }
    )

    return data


def create_result_forms_per_form_state(tally, electrol_race):
    ballot = create_ballot(tally, electrol_race)
    sub_con = create_sub_constituency(code=12345, tally=tally)
    center = create_center("12345", tally=tally, sub_constituency=sub_con)
    station = create_station(center)

    # create result forms :one result form for each state.
    for idx, enumKey in enumerate(FormState.__members__):
        single_enum = FormState[enumKey]
        barcode = f"11010010{idx}1"
        if not isinstance(single_enum.value, int):
            continue
        create_result_form(
            ballot=ballot,
            serial_number=idx,
            barcode=barcode,
            form_state=single_enum,
            center=center,
            station_number=station.station_number,
            tally=tally,
        )
    return tally


class TestBase(TestCase):
    @classmethod
    def _create_user(cls, username="bob", password="bob"):
        return UserProfile.objects.create(username=username, password=password)

    @classmethod
    def _get_request(cls, user=None):
        request = RequestFactory().get("/")
        request.user = (
            user
            if user is not None and isinstance(user, User)
            else AnonymousUser()
        )
        return request

    def _create_and_login_user(self, username="bob", password="bob"):
        """Create a user and user profile."""
        self.user = self._create_user(username, password)
        # to simulate login, assing user to a request object
        request = RequestFactory().get("/")
        request.user = self.user
        request.session = {}
        self.request = request

    def _create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, 13)

    def _add_user_to_group(self, user, name):
        if Group.objects.count() == 0:
            self._create_permission_groups()
        count = user.groups.count()
        add_user_to_group(user, name)
        self.assertTrue(user.groups.count() > count)
