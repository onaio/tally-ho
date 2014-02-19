from django.contrib.auth.models import User, Group, AnonymousUser
from django.utils import timezone

from django.test import TestCase
from django.test import RequestFactory

from libya_tally.apps.tally.models.audit import Audit
from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.apps.tally.models.candidate import Candidate
from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.clearance import Clearance
from libya_tally.apps.tally.models.office import Office
from libya_tally.apps.tally.models.reconciliation_form import\
    ReconciliationForm
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.station import Station
from libya_tally.apps.tally.models.sub_constituency import SubConstituency
from libya_tally.libs.models.enums.center_type import CenterType
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.enums.entry_version import EntryVersion
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.models.enums.race_type import RaceType
from libya_tally.libs.models.enums.gender import Gender
from libya_tally.libs.permissions.groups import create_permission_groups, \
    add_user_to_group


def create_audit(result_form, user, reviewed_team=False):
    return Audit.objects.create(user=user,
                                reviewed_team=reviewed_team,
                                result_form=result_form,
                                action_prior_to_recommendation=0,
                                resolution_recommendation=0)


def create_ballot():
    ballot, _ = Ballot.objects.get_or_create(number=1,
                                             race_type=RaceType.GENERAL)

    return ballot


def create_clearance(result_form, user, reviewed_team=False):
    date_team_modified = timezone.now() if reviewed_team else None

    return Clearance.objects.create(result_form=result_form,
                                    reviewed_team=reviewed_team,
                                    user=user,
                                    date_team_modified=date_team_modified
                                    )


def create_result(result_form, candidate, user, votes):
    Result.objects.create(result_form=result_form,
                          user=user,
                          candidate=candidate,
                          votes=votes,
                          entry_version=EntryVersion.FINAL)


def create_candidates(result_form, user,
                      name='the candidate name', votes=123,
                      women_name='women candidate name', num_results=10):
    for i in xrange(num_results):
        candidate = Candidate.objects.create(ballot=result_form.ballot,
                                             candidate_id=1,
                                             full_name=name,
                                             order=0,
                                             race_type=RaceType.GENERAL)
        candidate_f = Candidate.objects.create(ballot=result_form.ballot,
                                               candidate_id=1,
                                               full_name=women_name,
                                               order=0,
                                               race_type=RaceType.WOMEN)
        create_result(result_form, candidate, user, votes)
        create_result(result_form, candidate_f, user, votes)


def create_result_form(barcode='123456789', form_state=FormState.UNSUBMITTED,
                       ballot=None, station_number=None, center=None,
                       gender=Gender.MALE, force_ballot=True,
                       serial_number=0, user=None):
    if force_ballot and not ballot:
        ballot = create_ballot()

    result_form, _ = ResultForm.objects.get_or_create(
        ballot=ballot,
        barcode=barcode,
        serial_number=serial_number,
        form_state=form_state,
        station_number=station_number,
        user=user,
        center=center,
        gender=gender)

    return result_form


def center_data(code1, code2=None, station_number=1):
    if not code2:
        code2 = code1

    return {'center_number': code1,
            'center_number_copy': code2,
            'station_number': station_number,
            'station_number_copy': station_number}


def create_candidate(ballot, candidate_name, race_type=RaceType.GENERAL):
    return Candidate.objects.create(ballot=ballot,
                                    full_name=candidate_name,
                                    candidate_id=1,
                                    order=1,
                                    race_type=race_type)


def create_center(code='1'):
    return Center.objects.get_or_create(
        code=code,
        mahalla='1',
        name='1',
        office=create_office(),
        region='1',
        village='1',
        center_type=CenterType.GENERAL)[0]


def create_office(name='office'):
    return Office.objects.get_or_create(name=name)[0]


def create_reconciliation_form(
        result_form,
        entry_version=EntryVersion.FINAL,
        number_ballots_inside_box=1,
        number_unstamped_ballots=1):
    return ReconciliationForm.objects.create(
        result_form=result_form,
        ballot_number_from=1,
        ballot_number_to=1,
        number_ballots_received=1,
        number_signatures_in_vr=1,
        number_unused_ballots=1,
        number_spoiled_ballots=1,
        number_cancelled_ballots=1,
        number_ballots_outside_box=1,
        number_ballots_inside_box=number_ballots_inside_box,
        number_ballots_inside_and_outside_box=1,
        number_unstamped_ballots=number_unstamped_ballots,
        number_invalid_votes=1,
        number_valid_votes=1,
        number_sorted_and_counted=1,
        is_stamped=True,
        signature_polling_officer_1=True,
        signature_polling_officer_2=True,
        signature_polling_station_chair=True,
        signature_dated=True,
        entry_version=entry_version)


def create_recon_forms(result_form):
    recon1 = create_reconciliation_form(result_form)
    recon1.entry_version = EntryVersion.DATA_ENTRY_1
    recon1.save()

    recon2 = create_reconciliation_form(result_form)
    recon2.entry_version = EntryVersion.DATA_ENTRY_2
    recon2.save()


def create_station(center, registrants=1):
    sc, _ = SubConstituency.objects.get_or_create(code=1,
                                                  field_office='1')

    return Station.objects.get_or_create(
        center=center,
        sub_constituency=sc,
        gender=Gender.MALE,
        station_number=1,
        registrants=registrants)


def result_form_data_blank(result_form):
    return {'result_form': result_form.pk,
            'form-TOTAL_FORMS': [u'1'],
            'form-MAX_NUM_FORMS': [u'1000'],
            'form-INITIAL_FORMS': [u'0'],
            'form-0-votes': [u'']}


def result_form_data(result_form):
    data = result_form_data_blank(result_form)
    data.update({
        u'number_unstamped_ballots': [u'1'],
        u'number_ballots_inside_box': [u'1'],
        u'number_ballots_inside_and_outside_box': [u'1'],
        u'number_valid_votes': [u'1'],
        u'number_unused_ballots': [u'1'],
        u'number_spoiled_ballots': [u'1'],
        u'number_ballots_received': [u'1'],
        u'number_cancelled_ballots': [u'1'],
        u'ballot_number_from': [u'1'],
        u'number_ballots_outside_box': [u'1'],
        u'number_sorted_and_counted': [u'1'],
        u'number_invalid_votes': [u'1'],
        u'number_signatures_in_vr': [u'1'],
        u'ballot_number_to': [u'1'],
        u'form-0-votes': [u'1']
    })

    return data


class TestBase(TestCase):
    @classmethod
    def _create_user(cls, username='bob', password='bob'):
        return User.objects.create(username=username, password=password)

    @classmethod
    def _get_request(cls, user=None):
        request = RequestFactory().get('/')
        request.user = user \
            if user is not None and isinstance(user, User) else AnonymousUser()
        return request

    def _create_and_login_user(self, username='bob', password='bob'):
        self.user = self._create_user(username, password)
        # to simulate login, assing user to a request object
        request = RequestFactory().get('/')
        request.user = self.user
        self.request = request

    def _create_permission_groups(self):
        count = Group.objects.count()
        create_permission_groups()
        diff_count = Group.objects.count() - count
        self.assertEqual(diff_count, 14)

    def _add_user_to_group(self, user, name):
        if Group.objects.count() == 0:
            self._create_permission_groups()
        count = user.groups.count()
        add_user_to_group(user, name)
        self.assertTrue(user.groups.count() > count)
