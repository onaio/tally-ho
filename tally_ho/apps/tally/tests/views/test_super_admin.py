from django.core.exceptions import SuspiciousOperation
from django.contrib.messages.storage import default_storage
from django.test import RequestFactory

from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.views import super_admin as views
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    configure_messages,
    create_audit,
    create_ballot,
    create_candidates,
    create_reconciliation_form,
    create_result_form,
    create_center,
    create_station,
    create_tally,
    TestBase,
)


class TestSuperAdmin(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

    def test_form_action_view_post_invalid_audit(self):
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}

        with self.assertRaises(SuspiciousOperation):
            view(request, tally_id=tally.pk)

    def test_form_action_view_post_review_audit(self):
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {'result_form': result_form.pk,
                'review': 1}
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {'result_form': result_form.pk}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/audit/review', response['Location'])

    def test_form_action_view_post_confirm_audit(self):
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(form_state=FormState.AUDIT,
                                         tally=tally)
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
        response = view(request, tally_id=tally.pk)

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

    def test_result_export_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.ResultExportView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Downloads")

    def test_remove_center_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.RemoveCenterView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, 'name="center_number"')
        self.assertContains(response, '<form name="remove-center-form"')

    def test_remove_center_post_invalid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        view = views.RemoveCenterView.as_view()
        data = {
            'center_number': center.code,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response,
                            'Ensure this value has at least 5 character')

    def test_remove_center_post_valid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center('12345', tally=tally)
        view = views.RemoveCenterView.as_view()
        data = {
            'center_number': center.code,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        request.session = {}
        request._messages = default_storage(request)
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        # TODO this happens in RemoveCenterConfirmationView#delete
        # with self.assertRaises(Center.DoesNotExist):
        #     Center.objects.get(code=center.code)

    def test_remove_center_post_result_exists(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center('12345', tally=tally)
        result_form = create_result_form(center=center,
                                         form_state=FormState.AUDIT)
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        self.assertTrue(Result.objects.filter().count() > 0)

        view = views.RemoveCenterView.as_view()
        data = {
            'center_number': center.code,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, u"Results exist for barcodes")
        self.assertContains(response, result_form.barcode)

    def test_remove_center_link(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.DashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Remove a Center</a>")

    def test_remove_station_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.RemoveStationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, 'name="center_number"')
        self.assertContains(response, 'name="station_number"')
        self.assertContains(response, '<form name="remove-station-form"')

    def test_remove_station_post_invalid(self):
        station = 1
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        view = views.RemoveStationView.as_view()
        data = {
            'center_number': center.code,
            'station_number': station,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response,
                            'Ensure this value has at least 5 character')

    def test_remove_station_post_valid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center('12345', tally=tally)
        station = create_station(center)
        self.assertEqual(
            Station.objects.get(center__code=center.code,
                                station_number=station.station_number),
            station
        )
        view = views.RemoveStationView.as_view()
        data = {
            'center_number': center.code,
            'station_number': station.station_number,
            'station_id': station.pk,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        request.session = {}
        request._messages = default_storage(request)
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        # TODO this happens in RemoveStationConfirmationView#delete
        # with self.assertRaises(Station.DoesNotExist):
        #     Station.objects.get(center__code=center.code,
        #                         station_number=station.station_number)

    def test_remove_station_post_result_exists(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center('12345', tally=tally)
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
            'station_number': station.station_number,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, u"Results exist for barcodes")
        self.assertContains(response, result_form.barcode)

    def test_remove_station_link(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.DashboardView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Remove a Station</a>")

    def test_edit_station_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center('12345', tally=tally)
        station = create_station(center)
        view = views.EditStationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(
            request,
            station_id=station.pk,
            tally_id=tally.pk)
        self.assertContains(response, 'Edit Station')
        self.assertContains(response, '<td>%s</td>' % station.station_number)

    def test_edit_station_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        view = views.EditStationView.as_view()
        data = {
            'center_code': center.code,
            'station_number': station.station_number,
            'tally_id': tally.pk,
            'gender': station.gender.value,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        configure_messages(request)
        response = view(
            request,
            station_id=station.pk,
            tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)

    def test_create_center(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CreateCenterView.as_view()
        data = {
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        configure_messages(request)
        response = view(
            request,
            tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)

    def test_create_station(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CreateStationView.as_view()
        data = {
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        configure_messages(request)
        response = view(
            request,
            tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)

    def test_disable_entity_view_post_station_invalid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        view = views.DisableEntityView.as_view()
        data = {
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(
            request,
            center_code=center.code,
            station_number=station.station_number,
            tally_id=tally.pk)
        self.assertContains(response,
                            'This field is required')

    def test_disable_entity_view_post_station(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        comment_text = 'example comment text'
        view = views.DisableEntityView.as_view()
        data = {
            'center_code_input': center.code,
            'station_number_input': station.station_number,
            'tally_id': tally.pk,
            'comment_input': comment_text,
            'disable_reason': '2',
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(
            request,
            center_code=center.code,
            station_number=station.station_number,
            tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/data/center-list/%s/' % tally.pk, response['Location'])
        station.reload()
        self.assertEqual(station.disable_reason.value, 2)
        self.assertEqual(station.comments.all()[0].text, comment_text)

    def test_disable_entity_view_post_center(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        comment_text = 'example comment text'
        view = views.DisableEntityView.as_view()
        data = {
            'center_code_input': center.code,
            'comment_input': comment_text,
            'tally_id': tally.pk,
            'disable_reason': '2',
        }
        request = self.factory.post('/', data)
        request.user = self.user
        response = view(
            request,
            center_code=center.code,
            station_number=station.station_number,
            tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/data/center-list/%s/' % tally.pk, response['Location'])
        center.reload()
        self.assertEqual(center.disable_reason.value, 2)
        self.assertEqual(center.comments.all()[0].text, comment_text)

    def test_disable_race_view_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        comment_text = 'example comment text'
        view = views.DisableRaceView.as_view()
        data = {
            'race_id_input': ballot.pk,
            'comment_input': comment_text,
            'tally_id': tally.pk,
            'disable_reason': '2',
        }
        request = self.factory.post('/', data)
        request.user = self.user
        configure_messages(request)
        response = view(
            request,
            tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/data/race-list/%s/' % tally.pk, response['Location'])
        ballot.reload()
        self.assertEqual(ballot.disable_reason.value, 2)
        self.assertEqual(ballot.comments.all()[0].text, comment_text)

    def test_edit_race_view_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally)
        view = views.EditRaceView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(
            request,
            id=ballot.pk,
            tally_id=tally.pk)
        self.assertContains(response, 'Edit Race')
        self.assertContains(response, 'value="%s"' % ballot.number)

    def test_edit_race_view_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally)
        comment_text = 'jndfjs fsgfd'
        view = views.EditRaceView.as_view()
        data = {
            'comment_input': comment_text,
            'number': ballot.number,
            'race_type': ballot.race_type.value,
            'available_for_release': True,
            'race_id': ballot.pk,
            'tally_id': tally.pk,
        }
        request = self.factory.post('/', data)
        request.user = self.user
        configure_messages(request)
        response = view(
            request,
            id=ballot.pk,
            tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        ballot.reload()
        self.assertEqual(ballot.available_for_release, True)
        self.assertEqual(ballot.comments.first().text, comment_text)

    def test_form_duplicates_view_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormDuplicatesView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        response = view(
            request,
            tally_id=tally.pk)
        self.assertContains(response, 'Form Duplicates List')
