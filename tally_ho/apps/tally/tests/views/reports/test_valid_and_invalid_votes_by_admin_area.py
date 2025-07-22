import json

from bs4 import BeautifulSoup
from django.test import RequestFactory

from tally_ho.apps.tally.views.reports import (
    ValidAndInvalidVotesByAdminAreasDataView,
    ValidAndInvalidVotesByAdminAreasView)
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (TestBase, create_ballot,
                                           create_candidate_result,
                                           create_center, create_constituency,
                                           create_electrol_race, create_office,
                                           create_reconciliation_form,
                                           create_region, create_result_form,
                                           create_station,
                                           create_sub_constituency,
                                           create_tally)


class TestValidAndInvalidVotesByAdminArea(TestBase):
    """
    Test the valid and invalid votes by admin area report
    """
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
            ballot_name='Individual'
        )
        self.ballot = create_ballot(
            self.tally,
            electrol_race=self.electrol_race
        )
        self.region = create_region(
            tally=self.tally
        )
        self.office = create_office(
            tally=self.tally, region=self.region
        )
        self.constituency = create_constituency(
            tally=self.tally,
            name='Constituency 1'
        )
        self.sc = create_sub_constituency(
            code=1, field_office='1', ballots=[self.ballot],
            tally=self.tally
        )
        self.center = create_center(
            code='1', office_name=self.office.name, tally=self.tally,
            sub_constituency=self.sc, constituency=self.constituency
        )
        self.station =\
            create_station(
                center=self.center,
                registrants=100,
                tally=self.tally,
                station_number=1
            )
        self.result_form = create_result_form(
            tally=self.tally,
            form_state=FormState.ARCHIVED,
            office=self.office,
            center=self.center,
            station_number=self.station.station_number,
            ballot=self.ballot,
        )
        # Create candidate result (valid votes)
        self.valid_votes = 55
        create_candidate_result(
            self.result_form,
            votes=self.valid_votes,
            user=self.user,
            tally=self.tally
        )
        # Create reconciliation form (invalid votes)
        self.invalid_votes = 5
        create_reconciliation_form(
            result_form=self.result_form,
            user=self.user,
            number_valid_votes=self.valid_votes,
            number_invalid_votes=self.invalid_votes,
            entry_version=EntryVersion.FINAL,
        )

    def _get_html_headers(self, response):
        content = response.content.decode()
        doc = BeautifulSoup(content, "html.parser")
        return [
            header.text.strip() for header in doc.find('thead').findAll('th')]

    def test_html_view_region(self):
        """
        Test the HTML view for the region admin level
        """
        request =\
            self.factory.get(
                str(
                    '/reports/valid-and-invalid-votes-by-admin-area'
                    f'/{self.tally.pk}/region/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level='region')
        self.assertEqual(response.status_code, 200)
        response.render()
        headers = self._get_html_headers(response)
        self.assertEqual(
            headers, ['Region', 'Race Type', 'Valid Votes', 'Invalid Votes'])

    def test_html_view_office(self):
        """
        Test the HTML view for the office admin level
        """
        request =\
            self.factory.get(
                str(
                    '/reports/valid-and-invalid-votes-by-admin-area'
                    f'/{self.tally.pk}/office/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level='office')
        self.assertEqual(response.status_code, 200)
        response.render()
        headers = self._get_html_headers(response)
        self.assertEqual(
            headers, ['Office', 'Race Type', 'Valid Votes', 'Invalid Votes'])

    def test_html_view_constituency(self):
        """
        Test the HTML view for the constituency admin level
        """
        request =\
            self.factory.get(
                str(
                    '/reports/valid-and-invalid-votes-by-admin-area'
                    f'/{self.tally.pk}/constituency/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasView.as_view()
        response =\
            view(request, tally_id=self.tally.pk, admin_level='constituency')
        self.assertEqual(response.status_code, 200)
        response.render()
        headers = self._get_html_headers(response)
        self.assertEqual(
            headers,
            [
                'Main-Constituency',
                'Race Type',
                'Valid Votes',
                'Invalid Votes'
            ])

    def test_html_view_sub_constituency(self):
        """
        Test the HTML view for the sub constituency admin level
        """
        request =\
            self.factory.get(
                str(
                    '/reports/valid-and-invalid-votes-by-admin-area'
                    f'/{self.tally.pk}/sub_constituency/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasView.as_view()
        response =\
            view(
                request,
                tally_id=self.tally.pk,
                admin_level='sub_constituency'
            )
        self.assertEqual(response.status_code, 200)
        response.render()
        headers = self._get_html_headers(response)
        self.assertEqual(
            headers,
            ['Municipality', 'Race Type', 'Valid Votes', 'Invalid Votes']
        )

    def test_data_view_region(self):
        """
        Test the data view for the region admin level
        """
        request =\
            self.factory.post(
                str(
                    f'/data/valid-and-invalid-votes-by-adminarea-data'
                    f'/{self.tally.pk}/region/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasDataView.as_view()
        response =\
            view(
                request,
                tally_id=self.tally.pk,
                admin_level='region'
            )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        data = content.get('data')
        aggregate = content.get('aggregate')[0]
        # Only one row expected
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(
            row[0],
            '<td class="center">Region</td>'
        )
        self.assertEqual(
            row[2],
            '<td class="center">55</td>'
        )
        self.assertEqual(
            row[3],
            '<td class="center">5</td>'
        )
        # Aggregate
        self.assertEqual(
            aggregate[0],
            '<td class="center">Total</td>'
        )
        self.assertEqual(
            aggregate[2],
            '<td class="center">55</td>'
        )
        self.assertEqual(
            aggregate[3],
            '<td class="center">5</td>'
        )

    def test_data_view_office(self):
        """
        Test the data view for the office admin level
        """
        request =\
            self.factory.post(
                str(
                    f'/data/valid-and-invalid-votes-by-adminarea-data'
                    f'/{self.tally.pk}/office/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasDataView.as_view()
        response = view(request, tally_id=self.tally.pk, admin_level='office')
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        data = content.get('data')
        aggregate = content.get('aggregate')[0]
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(
            row[0],
            '<td class="center">office</td>')
        self.assertEqual(
            row[2], '<td class="center">55</td>')
        self.assertEqual(
            row[3], '<td class="center">5</td>')
        self.assertEqual(
            aggregate[0],
            '<td class="center">Total</td>')
        self.assertEqual(
            aggregate[2],
            '<td class="center">55</td>')
        self.assertEqual(
            aggregate[3],
            '<td class="center">5</td>')

    def test_data_view_constituency(self):
        """
        Test the data view for the constituency admin level
        """
        request =\
            self.factory.post(
                str(
                    f'/data/valid-and-invalid-votes-by-adminarea-data'
                    f'/{self.tally.pk}/constituency/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasDataView.as_view()
        response =\
            view(
                request,
                tally_id=self.tally.pk,
                admin_level='constituency'
            )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        data = content.get('data')
        aggregate = content.get('aggregate')[0]
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(
            row[0],
            str(
                '<td class="center">'
                'Constituency 1</td>'))
        self.assertEqual(
            row[2],
            '<td class="center">55</td>')
        self.assertEqual(
            row[3],
            '<td class="center">5</td>')
        self.assertEqual(
            aggregate[0],
            '<td class="center">Total</td>')
        self.assertEqual(
            aggregate[2],
            '<td class="center">55</td>')
        self.assertEqual(
            aggregate[3],
            '<td class="center">5</td>')

    def test_data_view_sub_constituency(self):
        """
        Test the data view for the sub constituency admin level
        """
        request =\
            self.factory.post(
                str(
                    f'/data/valid-and-invalid-votes-by-adminarea-data'
                    f'/{self.tally.pk}/sub_constituency/'
                )
            )
        request.user = self.user
        request.session = {}
        view = ValidAndInvalidVotesByAdminAreasDataView.as_view()
        response =\
            view(
                request,
                tally_id=self.tally.pk,
                admin_level='sub_constituency'
            )
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode())
        data = content.get('data')
        aggregate = content.get('aggregate')[0]
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(
            row[0],
            str(
                '<td class="center">'
                f'{self.sc.name}</td>'
            )
        )
        self.assertEqual(
            row[2],
            '<td class="center">55</td>'
        )
        self.assertEqual(
            row[3],
            '<td class="center">5</td>'
        )
        self.assertEqual(
            aggregate[0],
            '<td class="center">Total</td>'
        )
        self.assertEqual(
            aggregate[2],
            '<td class="center">55</td>'
        )
