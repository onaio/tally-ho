import json

from django.test import RequestFactory
from django.urls import reverse
from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser

from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.center import Center
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.apps.tally.views.reports.overvoted_forms import (
    OvervotedResultFormsView,
    OvervotedResultFormsDataView,
)
from tally_ho.libs.tests.test_base import (
    create_electrol_race,
    create_result_form,
    create_station,
    create_reconciliation_form,
    create_sub_constituency,
    create_tally,
    create_region,
    create_constituency,
    create_office,
    TestBase,
    create_ballot,
)

class TestOvervotedFormsViews(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally,
            election_level='Municipal',
            ballot_name='Individual',
        )
        ballot = create_ballot(
            self.tally,
            electrol_race=self.electrol_race,
        )
        self.region = create_region(tally=self.tally)
        office = create_office(tally=self.tally, region=self.region)
        self.constituency = create_constituency(tally=self.tally)
        self.sc = create_sub_constituency(
            code=1,
            field_office='1',
            ballots=[ballot],
            tally=self.tally,
        )
        center, _ = Center.objects.get_or_create(
            code='1',
            mahalla='1',
            name='1',
            office=office,
            region=self.region.name,
            village='1',
            active=True,
            tally=self.tally,
            sub_constituency=self.sc,
            center_type=CenterType.GENERAL,
            constituency=self.constituency,
        )
        self.station = create_station(
            center=center,
            registrants=50,
            tally=self.tally,
            station_number=1,
            gender=Gender.MALE,
        )
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=office,
            center=center,
            station_number=self.station.station_number,
            ballot=ballot,
        )
        self.recon_form = create_reconciliation_form(
            result_form=self.result_form,
            user=self.user,
            number_ballots_inside_box=60,  # Overvote
            number_cancelled_ballots=0,
            number_spoiled_ballots=0,
            number_unstamped_ballots=0,
            number_unused_ballots=40,
            number_valid_votes=55,
            number_invalid_votes=5,
            number_ballots_received=100,
            entry_version=EntryVersion.FINAL,
        )

    def test_overvoted_forms_view_renders(self):
        """
        Test that the overvoted forms view renders successfully and uses
        the correct template. Also check for key context variables in the
        rendered HTML.
        """
        request = self.factory.get(
            reverse('overvoted-forms', kwargs={'tally_id': self.tally.pk})
        )
        request.user = self.user
        request.session = {}
        response = OvervotedResultFormsView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)

        if hasattr(response, 'rendered_content'):
            content = response.rendered_content
        else:
            content = response.content.decode()
        doc = BeautifulSoup(content, "html.parser")

        table_headers = [th.text.strip() for th in doc.find_all('th')]
        expected_headers = [
            'Barcode', 'Center Code', 'Station Number', 'Ballots Inside',
            'Station Registrants', 'Race', 'Sub Race', 'Municipality Name',
            'Municipality Code',
        ]
        self.assertTrue(
            any(header in table_headers for header in expected_headers)
        )

        remote_url = reverse(
            'overvoted-forms-data', kwargs={'tally_id': self.tally.pk})
        self.assertIn(str(self.tally.pk), content)
        self.assertIn(remote_url, content)
        self.assertIn('deployedSiteUrl', content)

    def test_overvoted_forms_data_view_returns_data(self):
        """
        Test that the overvoted forms data endpoint returns expected data.
        """
        url = reverse(
            'overvoted-forms-data', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = self.user
        request.session = {}
        response = OvervotedResultFormsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        self.assertIn('data', content)
        self.assertGreaterEqual(len(content['data']), 1)

        row = content['data'][0]
        expected_keys = [
            'barcode', 'center_code', 'station_number', 'ballots_inside',
            'station_registrants', 'race', 'sub_race', 'municipality_name',
            'municipality_code',
        ]
        for key in expected_keys:
            self.assertIn(key, row)

        self.assertEqual(row['ballots_inside'], 60)
        self.assertEqual(row['station_registrants'], 50)

    def test_overvoted_forms_data_view_filtering(self):
        """
        Test filtering by search term in the data endpoint.
        """
        url = reverse(
            'overvoted-forms-data', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url, {'search[value]': 'Individual'})
        request.user = self.user
        request.session = {}
        response = OvervotedResultFormsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())

        search_term = 'Individual'
        for row in content['data']:
            self.assertTrue(
                any(search_term in\
                    str(value) for value in row.values())
            )

    def test_overvoted_forms_data_view_pagination(self):
        """
        Test pagination parameters in the data endpoint.
        """
        url = reverse(
            'overvoted-forms-data', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url, {'start': 0, 'length': 1})
        request.user = self.user
        request.session = {}
        response = OvervotedResultFormsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 1)

        row = content['data'][0]
        self.assertEqual(row['ballots_inside'], 60)

    def test_overvoted_forms_view_requires_login(self):
        """
        Test that the overvoted forms view requires login.
        """
        url = reverse(
            'overvoted-forms', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = AnonymousUser()
        request.session = {}
        response = OvervotedResultFormsView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertIn(response.status_code, [302, 403])

    def test_overvoted_forms_data_view_empty(self):
        """
        Test the data endpoint with no overvoted forms.
        """
        # Set ballots inside to less than registrants to remove overvote
        self.recon_form.number_ballots_inside_box = 10
        self.recon_form.save()
        url = reverse(
            'overvoted-forms-data', kwargs={'tally_id': self.tally.pk}
        )
        request = self.factory.get(url)
        request.user = self.user
        request.session = {}
        response = OvervotedResultFormsDataView.as_view()(
            request, tally_id=self.tally.pk
        )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())

        self.assertEqual(len(content['data']), 0)
