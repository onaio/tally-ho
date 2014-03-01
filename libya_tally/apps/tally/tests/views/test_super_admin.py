from django.core.exceptions import SuspiciousOperation
from django.contrib.messages.storage import default_storage
from django.test import RequestFactory

from libya_tally.apps.tally.models.center import Center
from libya_tally.apps.tally.models.result import Result
from libya_tally.apps.tally.models.station import Station
from libya_tally.apps.tally.views import super_admin as views
from libya_tally.libs.models.enums.form_state import FormState
from libya_tally.libs.permissions import groups
from libya_tally.libs.tests.test_base import create_audit,\
    create_candidates, create_reconciliation_form, create_result_form, \
    create_center, create_station, TestBase


class TestSuperAdmin(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_form_action_view_post_invalid_audit(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}

        with self.assertRaises(SuspiciousOperation):
            view(request)

    def test_form_action_view_post_review_audit(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk,
                'review': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/audit/review', response['Location'])

    def test_form_action_view_post_confirm_audit(self):
        result_form = create_result_form(form_state=FormState.AUDIT)
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        audit = create_audit(result_form, self.user)

        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk,
                'confirm': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request)

        audit.reload()
        result_form.reload()
        self.assertFalse(audit.active)
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)
        self.assertTrue(result_form.skip_quarantine_checks)

        self.assertEqual(len(result_form.results.all()), 20)
        self.assertEqual(len(result_form.reconciliationform_set.all()),
                         2)

        for result in result_form.results.all():
            self.assertFalse(result.active)

        for result in result_form.reconciliationform_set.all():
            self.assertFalse(result.active)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/super-administrator/form-action-list',
                      response['Location'])

    def test_form_not_received_list_view(self):
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Forms Not Received List")
        self.assertContains(response, "form_not_received.js")

    def test_form_not_received_list_csv_view(self):
        view = views.FormNotReceivedListView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, format='csv')
        self.assertContains(response, "Barcode")

    def test_result_export_view(self):
        view = views.ResultExportView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Downloads")

    def test_remove_center_get(self):
        view = views.RemoveCenterView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, 'name="center_number"')
        self.assertContains(response, '<form name="remove-center-form"')
        self.assertContains(response,
                            "confirm('Confirm that you want to "
                            "delete the centre!")

    def test_remove_center_post_invalid(self):
        view = views.RemoveCenterView.as_view()
        center = create_center()
        data = {'center_number': center.code}
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request)
        self.assertContains(response,
                            'Ensure this value has at least 5 character')

    def test_remove_center_post_valid(self):
        view = views.RemoveCenterView.as_view()
        center = create_center('12345')
        data = {'center_number': center.code}
        request = self.factory.post('/', data)
        request.user = self.user
        request.session = {}
        request._messages = default_storage(request)
        response = view(request)
        self.assertEqual(response.status_code, 302)
        with self.assertRaises(Center.DoesNotExist):
            Center.objects.get(code=center.code)

    def test_remove_center_post_result_exists(self):
        center = create_center('12345')
        result_form = create_result_form(center=center,
                                         form_state=FormState.AUDIT)
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        self.assertTrue(Result.objects.filter().count() > 0)

        view = views.RemoveCenterView.as_view()
        data = {'center_number': center.code}
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request)
        self.assertContains(response, u"Results exist for barcodes")
        self.assertContains(response, result_form.barcode)

    def test_remove_centre_link(self):
        view = views.DashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Remove a Centre</a>")

    def test_remove_station_get(self):
        view = views.RemoveStationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, 'name="center_number"')
        self.assertContains(response, 'name="station_number"')
        self.assertContains(response, '<form name="remove-station-form"')
        self.assertContains(response,
                            "confirm('Confirm that you want to "
                            "delete the station!")

    def test_remove_station_post_invalid(self):
        station = 1
        view = views.RemoveStationView.as_view()
        center = create_center()
        data = {
            'center_number': center.code,
            'station_number': station
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request)
        self.assertContains(response,
                            'Ensure this value has at least 5 character')

    def test_remove_station_post_valid(self):
        center = create_center('12345')
        station = create_station(center)
        self.assertEqual(
            Station.objects.get(center__code=center.code,
                                station_number=station.station_number),
            station
        )
        view = views.RemoveStationView.as_view()
        data = {
            'center_number': center.code,
            'station_number': station.station_number
        }
        request = self.factory.post('/', data)
        request.user = self.user
        request.session = {}
        request._messages = default_storage(request)
        response = view(request)
        self.assertEqual(response.status_code, 302)
        with self.assertRaises(Station.DoesNotExist):
            Station.objects.get(center__code=center.code,
                                station_number=station.station_number)

    def test_remove_station_post_result_exists(self):
        center = create_center('12345')
        station = create_station(center)
        result_form = create_result_form(center=center,
                                         form_state=FormState.AUDIT,
                                         station_number=station.station_number)
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        self.assertTrue(Result.objects.filter().count() > 0)

        view = views.RemoveStationView.as_view()
        data = {
            'center_number': center.code,
            'station_number': station.station_number
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request)
        self.assertContains(response, u"Results exist for barcodes")
        self.assertContains(response, result_form.barcode)

    def test_remove_station_link(self):
        view = views.DashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request)
        self.assertContains(response, "Remove a Station</a>")
