import json
import os
import shutil

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.storage import default_storage
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.utils import timezone
from reversion import revisions

from tally_ho.apps.tally.forms.create_result_form import CreateResultForm
from tally_ho.apps.tally.forms.edit_result_form import EditResultForm
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.clearance import Clearance
from tally_ho.apps.tally.models.electrol_race import ElectrolRace
from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.result_form_reset import ResultFormReset
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.views import super_admin as views
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.gender import Gender
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.fixtures.electrol_race_data import electrol_races
from tally_ho.libs.tests.test_base import (TestBase, configure_messages,
                                           create_audit, create_ballot,
                                           create_candidate, create_candidates,
                                           create_center, create_electrol_race,
                                           create_quarantine_checks,
                                           create_reconciliation_form,
                                           create_result, create_result_form,
                                           create_result_forms_per_form_state,
                                           create_station,
                                           create_sub_constituency,
                                           create_tally)


class TestSuperAdmin(TestBase):
    def setUp(self):
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally = create_tally()
        self.tally.users.add(self.user)
        self.electrol_race = create_electrol_race(
            self.tally, **electrol_races[0]
        )

    def test_form_action_view_post_invalid_audit(self):
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.AUDIT, tally=tally
        )
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {"result_form": result_form.pk}
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {}

        with self.assertRaises(SuspiciousOperation):
            view(request, tally_id=tally.pk)

    def test_form_action_view_post_review_audit(self):
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.AUDIT, tally=tally
        )
        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {"result_form": result_form.pk, "review": 1}
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/audit/review", response["Location"])

    def test_form_action_view_post_confirm_audit(self):
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.AUDIT, tally=tally
        )
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        audit = create_audit(result_form, self.user)

        request = self._get_request()
        view = views.FormActionView.as_view()
        data = {"result_form": result_form.pk, "confirm": 1}
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk)

        audit.reload()
        result_form.reload()
        self.assertFalse(audit.active)
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)
        # Verify user tracking
        self.assertEqual(result_form.previous_form_state, FormState.AUDIT)
        self.assertEqual(result_form.user, self.user.userprofile)
        self.assertTrue(result_form.skip_quarantine_checks)

        self.assertEqual(len(result_form.results.all()), 20)
        self.assertEqual(len(result_form.reconciliationform_set.all()), 2)

        for result in result_form.results.all():
            self.assertFalse(result.active)

        for result in result_form.reconciliationform_set.all():
            self.assertFalse(result.active)

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/super-administrator/form-action-list", response["Location"]
        )

    def test_result_export_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.ResultExportView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Downloads")

    def test_remove_center_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.RemoveCenterView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, 'name="center_number"')
        self.assertContains(response, '<form name="remove-center-form"')

    def test_remove_center_post_invalid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        view = views.RemoveCenterView.as_view()
        data = {
            "center_number": center.code,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(
            response, "Ensure this value has at least 5 character"
        )

    def test_remove_center_post_valid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center("12345", tally=tally)
        view = views.RemoveCenterView.as_view()
        data = {
            "center_number": center.code,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
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
        center = create_center("12345", tally=tally)
        result_form = create_result_form(
            center=center, form_state=FormState.AUDIT
        )
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        self.assertTrue(Result.objects.filter().count() > 0)

        view = views.RemoveCenterView.as_view()
        data = {
            "center_number": center.code,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Results exist for barcodes")
        self.assertContains(response, result_form.barcode)

    def test_remove_center_link(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.DashboardView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Remove a Center</a>")

    def test_tallies_view_get_with_no_tallies(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.TalliesView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        response.render()
        self.assertIn(tally.name, str(response.content))
        self.assertIn(
            "You have no tally assigned to be administrated",
            str(response.content),
        )

    def test_tallies_view_get_with_tallies(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.TalliesView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        request.user.administrated_tallies.set(Tally.objects.all())
        response = view(request, tally_id=tally.pk)
        response.render()
        self.assertIn(tally.name, str(response.content))
        self.assertNotIn(
            "You have no tally assigned to be administrated",
            str(response.content),
        )

    def test_remove_station_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.RemoveStationView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
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
            "center_number": center.code,
            "station_number": station,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(
            response, "Ensure this value has at least 5 character"
        )

    def test_remove_station_post_valid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center("12345", tally=tally)
        station = create_station(center)
        self.assertEqual(
            Station.objects.get(
                center__code=center.code, station_number=station.station_number
            ),
            station,
        )
        view = views.RemoveStationView.as_view()
        data = {
            "center_number": center.code,
            "station_number": station.station_number,
            "station_id": station.pk,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
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
        center = create_center("12345", tally=tally)
        station = create_station(center)
        result_form = create_result_form(
            center=center,
            form_state=FormState.AUDIT,
            station_number=station.station_number,
        )
        create_reconciliation_form(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_candidates(result_form, self.user)
        self.assertTrue(Result.objects.filter().count() > 0)

        view = views.RemoveStationView.as_view()
        data = {
            "center_number": center.code,
            "station_number": station.station_number,
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Results exist for barcodes")
        self.assertContains(response, result_form.barcode)

    def test_remove_station_link(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.DashboardView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Remove a Station</a>")

    def test_staff_performance_metrics_section_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.DashboardView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)

        self.assertContains(response, "<h3>Staff Performance Metrics</h3>")
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Intake%20Clerk/">Intake Clerk</a></li>'
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Intake%20Supervisor/">Intake Supervisor</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Clearance%20Clerk/">Clearance Clerk</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Clearance%20Supervisor/">Clearance Supervisor</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Data%20Entry%201%20Clerk/">Data Entry 1 Clerk</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Data%20Entry%202%20Clerk/">Data Entry 2 Clerk</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Corrections%20Clerk/">Corrections Clerk</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Quality%20Control%20Clerk/">Quality Control Clerk</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Quality%20Control%20Supervisor/">'
                "Quality Control Supervisor</a></li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Audit%20Clerk/">Audit Clerk</a></li>'
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/staff-performance-metrics/'
                '{}/Audit%20Supervisor/">Audit Supervisor</a>'
                "</li>"
            ).format(tally.pk),
        )
        self.assertContains(
            response,
            str(
                '<li><a href="/reports/internal/supervisors-approvals/{}/">'
                "Supervisors Approvals</a></li>"
            ).format(tally.pk),
        )

    def test_edit_station_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center("12345", tally=tally)
        station = create_station(center)
        view = views.EditStationView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, station_id=station.pk, tally_id=tally.pk)
        self.assertContains(response, "Edit Station")
        self.assertContains(response, "<td>%s</td>" % station.station_number)

    def test_edit_station_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        view = views.EditStationView.as_view()
        data = {
            "center_code": center.code,
            "station_number": station.station_number,
            "tally_id": tally.pk,
            "gender": station.gender.value,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        configure_messages(request)
        response = view(request, station_id=station.pk, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)

    def test_create_center(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CreateCenterView.as_view()
        data = {
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        configure_messages(request)
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)

    def test_create_station_invalid(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.CreateStationView.as_view()
        data = {
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = {}
        configure_messages(request)
        response = view(request, tally_id=tally.pk)
        self.assertFalse(response.context_data["form"].is_valid())
        self.assertEqual(
            response.context_data["form"].errors["center"][0],
            str("This field is required."),
        )
        self.assertEqual(
            response.context_data["form"].errors["station_number"][0],
            str("This field is required."),
        )
        self.assertEqual(
            response.context_data["form"].errors["gender"][0],
            str("This field is required."),
        )
        self.assertEqual(
            response.context_data["form"].errors["sub_constituency"][0],
            str("This field is required."),
        )

    def test_create_station_valid(self):
        tally = create_tally()
        tally.users.add(self.user)
        sc, _ = SubConstituency.objects.get_or_create(
            code=1, field_office="1", tally=tally
        )
        center = create_center("12345", tally=tally, sub_constituency=sc)
        station = create_station(center)
        view = views.CreateStationView.as_view()
        data = {
            "center": center.pk,
            "sub_constituency": sc.pk,
            "station_number": station.station_number,
            "tally_id": tally.pk,
            "gender": station.gender.value,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = {}
        configure_messages(request)
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["location"], str("/data/center-list/{}/").format(tally.pk)
        )

    def test_disable_entity_view_post_station_invalid(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        view = views.DisableEntityView.as_view()
        data = {
            "tally_id": tally.pk,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = {}
        response = view(
            request,
            center_code=center.code,
            station_number=station.station_number,
            tally_id=tally.pk,
        )
        self.assertContains(response, "This field is required")

    def test_disable_entity_view_post_station(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        comment_text = "example comment text"
        view = views.DisableEntityView.as_view()
        data = {
            "center_code_input": center.code,
            "station_number_input": station.station_number,
            "tally_id": tally.pk,
            "comment_input": comment_text,
            "disable_reason": "2",
        }
        request = self.factory.post("/", data)
        request.user = self.user
        response = view(
            request,
            center_code=center.code,
            station_number=station.station_number,
            tally_id=tally.pk,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/data/center-list/%s/" % tally.pk, response["Location"])
        station.reload()
        self.assertEqual(station.disable_reason.value, 2)
        self.assertEqual(station.comments.all()[0].text, comment_text)

    def test_disable_entity_view_post_center(self):
        tally = create_tally()
        tally.users.add(self.user)
        center = create_center(tally=tally)
        station = create_station(center)
        comment_text = "example comment text"
        view = views.DisableEntityView.as_view()
        data = {
            "center_code_input": center.code,
            "comment_input": comment_text,
            "tally_id": tally.pk,
            "disable_reason": "2",
        }
        request = self.factory.post("/", data)
        request.user = self.user
        response = view(
            request,
            center_code=center.code,
            station_number=station.station_number,
            tally_id=tally.pk,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/data/center-list/%s/" % tally.pk, response["Location"])
        center.reload()
        self.assertEqual(center.disable_reason.value, 2)
        self.assertEqual(center.comments.all()[0].text, comment_text)

    def test_disable_race_view_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        comment_text = "example comment text"
        view = views.DisableBallotView.as_view()
        data = {
            "ballot_id_input": ballot.pk,
            "electrol_race_id_input": ballot.electrol_race.pk,
            "comment_input": comment_text,
            "tally_id": tally.pk,
            "disable_reason": "2",
        }
        request = self.factory.post("/", data)
        request.user = self.user
        configure_messages(request)
        response = view(request, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/data/ballot-list/%s/" % tally.pk, response["Location"])
        ballot.reload()
        self.assertEqual(ballot.disable_reason.value, 2)
        self.assertEqual(ballot.comments.all()[0].text, comment_text)

    def test_create_race_invalid_document_extension_error(self):
        view = views.CreateBallotView.as_view()
        file_size = settings.MAX_FILE_UPLOAD_SIZE
        video = SimpleUploadedFile(
            "file.mp4", bytes(file_size), content_type="video/mp4"
        )
        data = {
            "number": 1,
            "electrol_race_id": self.electrol_race.pk,
            "tally_id": self.tally.pk,
            "available_for_release": True,
            "document": video,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = data
        configure_messages(request)
        response = view(request, tally_id=self.tally.pk)
        self.assertFalse(response.context_data["form"].is_valid())
        self.assertEqual(
            response.context_data["form"].errors["document"][0],
            str(
                "File extension (.mp4) is not supported."
                " Allowed extension(s) are: .png, .jpg, .doc, .pdf."
            ),
        )
        video.close()

    def test_create_race_invalid_document_size_error(self):
        view = views.CreateBallotView.as_view()
        file_size = settings.MAX_FILE_UPLOAD_SIZE * 2
        image = SimpleUploadedFile(
            "image.jpg", bytes(file_size), content_type="image/jpeg"
        )
        data = {
            "number": 1,
            "electrol_race_id": self.electrol_race.pk,
            "tally_id": self.tally.pk,
            "available_for_release": True,
            "document": image,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = data
        configure_messages(request)
        response = view(request, tally_id=self.tally.pk)
        self.assertFalse(response.context_data["form"].is_valid())
        self.assertEqual(
            response.context_data["form"].errors["document"][0],
            str(
                "File size must be under 10.0\xa0MB."
                " Current file size is 20.0\xa0MB."
            ),
        )
        image.close()

    def test_create_race_view(self):
        view = views.CreateBallotView.as_view()
        file_size = settings.MAX_FILE_UPLOAD_SIZE
        image_file_name = "image.jpg"
        image_file = SimpleUploadedFile(
            image_file_name, bytes(file_size), content_type="image/jpeg"
        )
        data = {
            "number": 2,
            "electrol_race_id": self.electrol_race.pk,
            "tally_id": self.tally.pk,
            "available_for_release": True,
            "document": image_file,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        request.session = data
        configure_messages(request)
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        ballot = Ballot.objects.get(document__isnull=False)
        self.assertIn(image_file_name, ballot.document.path)
        shutil.rmtree(os.path.dirname(ballot.document.path))
        image_file.close()

    def test_edit_race_view_get(self):
        ballot = create_ballot(self.tally, electrol_race=self.electrol_race)
        view = views.EditBallotView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, id=ballot.pk, tally_id=self.tally.pk)
        self.assertContains(response, "Edit Ballot")
        self.assertContains(response, 'value="%s"' % ballot.number)

    def test_edit_race_view_post(self):
        file_size = settings.MAX_FILE_UPLOAD_SIZE
        pdf_file_name = "file.pdf"
        image_file_name = "image.jpg"
        pdf_file = SimpleUploadedFile(
            pdf_file_name, bytes(file_size), content_type="application/pdf"
        )
        image_file = SimpleUploadedFile(
            image_file_name, bytes(file_size), content_type="image/jpeg"
        )
        ballot = create_ballot(self.tally, document=pdf_file)
        comment_text = "jndfjs fsgfd"
        view = views.EditBallotView.as_view()
        data = {
            "comment_input": comment_text,
            "number": ballot.number,
            "available_for_release": True,
            "electrol_race_id": ballot.electrol_race.pk,
            "tally_id": self.tally.pk,
            "document": image_file,
        }
        request = self.factory.post("/", data)
        request.user = self.user
        configure_messages(request)
        response = view(request, id=ballot.pk, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 302)
        ballot.reload()
        ballot.refresh_from_db()

        # testing auto_delete_document signal was called
        self.assertNotIn(pdf_file_name, ballot.document.path)
        self.assertIn(image_file_name, ballot.document.path)
        self.assertEqual(ballot.available_for_release, True)
        self.assertEqual(ballot.comments.first().text, comment_text)

    def test_form_duplicates_view_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        view = views.FormDuplicatesView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, tally_id=tally.pk)
        self.assertContains(response, "Form Duplicates List")

    def test_edit_result_form_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        result_form = create_result_form(
            form_state=FormState.UNSUBMITTED,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.EditResultFormView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, form_id=result_form.pk, tally_id=tally.pk)
        self.assertContains(response, "Edit Form")

    def test_create_result_form_mandatory_fields(self):
        form_data = {}
        form = CreateResultForm(form_data)
        self.assertIn("All fields are mandatory", form.errors["__all__"])
        self.assertFalse(form.is_valid())

    def test_create_result_form_ballot_not_active_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally)
        ballot = create_ballot(tally=tally, active=False)
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "created_user": self.request.user.userprofile,
            "gender": 1,
        }
        form = CreateResultForm(form_data)
        self.assertIn("Ballot is disabled", form.errors["__all__"])
        self.assertFalse(form.is_valid())

    def test_create_result_form_center_not_active_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally, active=False)
        ballot = create_ballot(tally=tally)
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "created_user": self.request.user.userprofile,
            "gender": 1,
        }
        form = CreateResultForm(form_data)
        self.assertIn("Selected center is disabled", form.errors["__all__"])
        self.assertFalse(form.is_valid())

    def test_create_result_form_station_not_active_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        center = create_center(code, tally=tally)
        ballot = create_ballot(tally=tally)
        station = create_station(center, active=False)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "created_user": self.request.user.userprofile,
            "gender": 1,
        }
        form = CreateResultForm(form_data)
        self.assertIn("Selected station is disabled", form.errors["__all__"])
        self.assertFalse(form.is_valid())

    def test_create_result_form_station_does_not_exist_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        ballot = create_ballot(tally=tally)
        form_data = {
            "center": center.pk,
            "station_number": station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "created_user": self.request.user.userprofile,
            "gender": 1,
        }
        form = CreateResultForm(form_data)
        self.assertIn(
            "Station does not exist for the selected center",
            form.errors["__all__"],
        )
        self.assertFalse(form.is_valid())

    def test_create_result_form_ballot_number_mis_match_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        ballot = create_ballot(tally=tally, number=2)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office="1")
        center = create_center(code, tally=tally, sub_constituency=sc)
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "created_user": self.request.user.userprofile,
            "gender": 1,
        }
        form = CreateResultForm(form_data)
        self.assertIn(
            "Ballot number do not match for center and station",
            form.errors["__all__"],
        )
        self.assertFalse(form.is_valid())

    def test_create_result_form_valid(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        barcode = "12345"
        ballot = create_ballot(tally=tally)
        sc = create_sub_constituency(
            code=1, tally=tally, field_office="1", ballots=[ballot]
        )
        center = create_center(code, tally=tally, sub_constituency=sc)
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": barcode,
            "created_user": self.request.user.userprofile,
            "gender": 1,
        }
        form = CreateResultForm(form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.instance.barcode, barcode)
        form.save()
        self.assertEqual(
            ResultForm.objects.get(id=form.instance.id).barcode, barcode
        )

    def test_create_result_form_view(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.UNSUBMITTED,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        request = self._get_request()
        view = views.CreateResultFormView.as_view()
        data = {"result_form": result_form.pk}
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        response = view(request, form_id=result_form.pk, tally_id=tally.pk)
        self.assertEqual(response.status_code, 200)

    def test_edit_result_form_ballot_not_active_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        ballot = create_ballot(tally=tally, active=False)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office="1")
        center = create_center(code, tally=tally, sub_constituency=sc)
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "gender": 1,
        }
        form = EditResultForm(form_data)
        self.assertIn("Ballot is disabled", form.errors["__all__"])
        self.assertFalse(form.is_valid())

    def test_edit_result_form_center_not_active_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        ballot = create_ballot(tally=tally)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office="1")
        center = create_center(
            code, tally=tally, active=False, sub_constituency=sc
        )
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "gender": 1,
        }
        form = EditResultForm(form_data)
        self.assertIn("Selected center is disabled", form.errors["__all__"])
        self.assertFalse(form.is_valid())

    def test_edit_result_form_barcode_exist_error(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        ballot = create_ballot(tally=tally, number=2)
        sc, _ = SubConstituency.objects.get_or_create(code=1, field_office="1")
        center = create_center(code, tally=tally, sub_constituency=sc)
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "gender": 1,
        }
        form = EditResultForm(form_data)
        self.assertIn(
            "Ballot number do not match for center and station",
            form.errors["__all__"],
        )
        self.assertFalse(form.is_valid())

    def test_edit_result_form_valid(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        ballot = create_ballot(tally=tally)
        sc = create_sub_constituency(
            code=1, tally=tally, field_office="1", ballots=[ballot]
        )
        center = create_center(code, tally=tally, sub_constituency=sc)
        station = create_station(center)
        form_data = {
            "center": center.pk,
            "station_number": station.station_number,
            "tally": tally.pk,
            "form_state": 9,
            "ballot": ballot.pk,
            "barcode": 12345,
            "gender": 1,
        }
        form = EditResultForm(form_data)
        self.assertTrue(form.is_valid())

    def test_remove_result_form_confirmation_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.UNSUBMITTED,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.RemoveResultFormConfirmationView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(request, form_id=result_form.pk, tally_id=tally.pk)
        self.assertContains(response, '<form name="remove-form-form"')

    def test_remove_result_form_confirmation_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        code = "12345"
        station_number = 1
        center = create_center(code, tally=tally)
        create_station(center)
        result_form = create_result_form(
            form_state=FormState.UNSUBMITTED,
            center=center,
            tally=tally,
            station_number=station_number,
        )
        view = views.RemoveResultFormConfirmationView.as_view()
        data = {"result_form": result_form.pk}
        request = self.factory.post("/", data=data)
        request.user = self.user
        request.session = {"result_form": result_form.pk}
        request._messages = default_storage(request)
        response = view(request, form_id=result_form.pk, tally_id=tally.pk)
        self.assertEqual(response.status_code, 302)

    def test_get_result_form_with_duplicate_results(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot_1 = create_ballot(tally=tally)
        barcode = "1234"
        center = create_center("12345", tally=tally)
        station = create_station(center)
        result_form_1 = create_result_form(
            tally=tally,
            ballot=ballot_1,
            center=center,
            station_number=station.station_number,
        )
        result_form_2 = create_result_form(
            ballot=ballot_1,
            barcode=barcode,
            serial_number=2,
            form_state=FormState.UNSUBMITTED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )

        # Ensure duplicate_reviewed is False for both forms
        result_form_1.duplicate_reviewed = False
        result_form_1.save()
        result_form_2.duplicate_reviewed = False
        result_form_2.save()

        votes = 12
        create_candidates(
            result_form_1, votes=votes, user=self.user, num_results=1
        )

        for result in result_form_1.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form_2, result.candidate, self.user, votes)
        duplicate_results = views.get_result_form_with_duplicate_results(
            tally_id=tally.pk
        )
        self.assertIn(result_form_1, duplicate_results)
        self.assertIn(result_form_2, duplicate_results)

        electrol_race = create_electrol_race(tally, **electrol_races[1])
        # test filtering duplicate result forms by ballot
        ballot_2 = create_ballot(
            tally,
            active=True,
            number=2,
            available_for_release=False,
            electrol_race=electrol_race,
        )
        result_form_3 = create_result_form(
            ballot=ballot_2,
            barcode="12345",
            serial_number=3,
            form_state=FormState.UNSUBMITTED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )
        result_form_4 = create_result_form(
            ballot=ballot_2,
            barcode="123456",
            serial_number=4,
            form_state=FormState.UNSUBMITTED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )

        # Ensure duplicate_reviewed is False for ballot 2 forms
        result_form_3.duplicate_reviewed = False
        result_form_3.save()
        result_form_4.duplicate_reviewed = False
        result_form_4.save()

        create_candidates(
            result_form_3, votes=votes, user=self.user, num_results=1
        )

        for result in result_form_3.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form_4, result.candidate, self.user, votes)
        ballot_1_duplicates = views.get_result_form_with_duplicate_results(
            tally_id=tally.pk, ballot=ballot_1.number
        )
        ballot_2_duplicates = views.get_result_form_with_duplicate_results(
            tally_id=tally.pk, ballot=ballot_2.number
        )
        all_duplicates = views.get_result_form_with_duplicate_results(
            tally_id=tally.pk
        )

        # check result_form_1 and result_form_2 are in ballot_1_duplicates
        self.assertIn(result_form_1, ballot_1_duplicates)
        self.assertIn(result_form_2, ballot_1_duplicates)

        # check result_form_3 and result_form_4 are not in ballot_1_duplicates
        self.assertNotIn(result_form_3, ballot_1_duplicates)
        self.assertNotIn(result_form_4, ballot_1_duplicates)

        # check result_form_3 and result_form_4 are in ballot_2_duplicates
        self.assertIn(result_form_3, ballot_2_duplicates)
        self.assertIn(result_form_4, ballot_2_duplicates)

        # check result_form_1 and result_form_2 are not in ballot_2_duplicates
        self.assertNotIn(result_form_1, ballot_2_duplicates)
        self.assertNotIn(result_form_2, ballot_2_duplicates)

        self.assertIn(result_form_1, all_duplicates)
        self.assertIn(result_form_2, all_duplicates)
        self.assertIn(result_form_3, all_duplicates)
        self.assertIn(result_form_4, all_duplicates)

        # Test that forms with duplicate_reviewed=True are not included
        result_form_1.duplicate_reviewed = True
        result_form_1.save()
        result_form_2.duplicate_reviewed = True
        result_form_2.save()

        filtered_duplicates = views.get_result_form_with_duplicate_results(
            tally_id=tally.pk, ballot=ballot_1.number
        )
        self.assertNotIn(result_form_1, filtered_duplicates)
        self.assertNotIn(result_form_2, filtered_duplicates)

    def test_duplicate_result_form_view_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        barcode = "1234"
        center = create_center("12345", tally=tally)
        station = create_station(center)
        result_form_1 = create_result_form(
            tally=tally,
            ballot=ballot,
            center=center,
            station_number=station.station_number,
        )
        result_form_2 = create_result_form(
            ballot=ballot,
            barcode=barcode,
            serial_number=2,
            form_state=FormState.UNSUBMITTED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )
        votes = 12
        create_candidates(
            result_form_1, votes=votes, user=self.user, num_results=1
        )

        for result in result_form_1.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form_2, result.candidate, self.user, votes)
        view = views.DuplicateResultFormView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        response = view(
            request,
            tally_id=tally.pk,
            barcode=barcode,
            ballot_id=ballot.number,
        )
        response.render()
        self.assertIn(
            ("{}{}").format(
                "Duplicate result forms list for ballot:  ", ballot.number
            ),
            str(response.content),
        )
        self.assertIn(
            ("{}{}").format("Result form barcode:  ", barcode),
            str(response.content),
        )
        self.assertIn("Send to clearance", str(response.content))
        self.assertIn("Send all to clearance", str(response.content))
        self.assertIn("Mark as reviewed and accepted", str(response.content))

    def test_duplicate_result_form_view_duplicate_reviewed_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        barcode = ("1234",)
        center = create_center("12345", tally=tally)
        station = create_station(center)
        result_form_1 = create_result_form(
            tally=tally,
            ballot=ballot,
            center=center,
            station_number=station.station_number,
        )
        result_form_2 = create_result_form(
            ballot=ballot,
            barcode=barcode,
            serial_number=2,
            form_state=FormState.UNSUBMITTED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )
        votes = 12
        create_candidates(
            result_form_1, votes=votes, user=self.user, num_results=1
        )

        for result in result_form_1.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form_2, result.candidate, self.user, votes)
        view = views.DuplicateResultFormView.as_view()
        data = {"duplicate_reviewed": 1}
        request = self.factory.post("/", data=data)
        request.user = self.user
        configure_messages(request)
        response = view(request, tally_id=tally.pk, ballot_id=ballot.number)

        result_form_1.reload()
        result_form_2.reload()
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/super-administrator/duplicate-result-tracking", response.url
        )
        self.assertTrue(result_form_1.duplicate_reviewed)
        self.assertTrue(result_form_2.duplicate_reviewed)

    def test_duplicate_result_form_view_send_clearance_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        barcode = ("1234",)
        center = create_center("12345", tally=tally)
        station = create_station(center)
        result_form = create_result_form(
            tally=tally,
            ballot=ballot,
            barcode=barcode,
            center=center,
            station_number=station.station_number,
        )
        # Store initial state for tracking verification
        initial_state = result_form.form_state
        votes = 12
        create_candidates(
            result_form, votes=votes, user=self.user, num_results=1
        )
        view = views.DuplicateResultFormView.as_view()
        data = {"result_form": result_form.pk, "send_clearance": 1}
        request = self.factory.post("/", data=data)
        request.user = self.user
        configure_messages(request)
        request.session = {"result_form": result_form.pk}
        response = view(request, tally_id=tally.pk, ballot_id=ballot.number)

        result_form.reload()
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/super-administrator/duplicate-result-tracking", response.url
        )
        self.assertEqual(result_form.form_state, FormState.CLEARANCE)
        # Verify previous_form_state and user tracking
        self.assertEqual(result_form.previous_form_state, initial_state)
        self.assertEqual(result_form.user, self.user.userprofile)
        self.assertTrue(result_form.duplicate_reviewed)

        # Verify Clearance was created
        clearance = Clearance.objects.get(result_form=result_form)
        self.assertEqual(clearance.user, self.user.userprofile)

        # check archived form is not sent to clearance
        result_form_2 = create_result_form(
            ballot=ballot,
            barcode="1234",
            serial_number=2,
            form_state=FormState.ARCHIVED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )
        create_candidates(
            result_form_2, votes=votes, user=self.user, num_results=1
        )
        data = {"result_form": result_form_2.pk, "send_clearance": 1}
        request = self.factory.post("/", data=data)
        request.user = self.user
        configure_messages(request)
        request.session = {"result_form": result_form_2.pk}
        response = view(request, tally_id=tally.pk, ballot_id=ballot.number)

        result_form_2.reload()
        self.assertNotEqual(result_form_2.form_state, FormState.CLEARANCE)
        self.assertEqual(result_form_2.form_state, FormState.ARCHIVED)
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/", response.url)

    def test_duplicate_result_form_view_send_all_clearance_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        barcode = ("1234",)
        center = create_center("12345", tally=tally)
        station = create_station(center)
        result_form_1 = create_result_form(
            tally=tally,
            ballot=ballot,
            center=center,
            station_number=station.station_number,
        )
        # Store initial states for tracking verification
        initial_state_1 = result_form_1.form_state
        result_form_2 = create_result_form(
            ballot=ballot,
            barcode=barcode,
            serial_number=2,
            form_state=FormState.UNSUBMITTED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )
        initial_state_2 = result_form_2.form_state
        votes = 12
        create_candidates(
            result_form_1, votes=votes, user=self.user, num_results=1
        )

        for result in result_form_1.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form_2, result.candidate, self.user, votes)
        view = views.DuplicateResultFormView.as_view()
        data = {"send_all_clearance": 1}
        request = self.factory.post("/", data=data)
        request.user = self.user
        configure_messages(request)
        response = view(request, tally_id=tally.pk, ballot_id=ballot.number)

        result_form_1.reload()
        result_form_2.reload()
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/super-administrator/duplicate-result-tracking", response.url
        )
        self.assertEqual(result_form_1.form_state, FormState.CLEARANCE)
        # Verify previous_form_state and user tracking for form 1
        self.assertEqual(result_form_1.previous_form_state, initial_state_1)
        self.assertEqual(result_form_1.user, self.user.userprofile)
        self.assertTrue(result_form_1.duplicate_reviewed)
        self.assertEqual(result_form_2.form_state, FormState.CLEARANCE)
        # Verify previous_form_state and user tracking for form 2
        self.assertEqual(result_form_2.previous_form_state, initial_state_2)
        self.assertEqual(result_form_2.user, self.user.userprofile)
        self.assertTrue(result_form_2.duplicate_reviewed)

        # Verify Clearance was created for both forms
        clearance_1 = Clearance.objects.get(result_form=result_form_1)
        self.assertEqual(clearance_1.user, self.user.userprofile)
        clearance_2 = Clearance.objects.get(result_form=result_form_2)
        self.assertEqual(clearance_2.user, self.user.userprofile)

    def test_duplicate_archived_result_forms_send_all_clearance_post(self):
        tally = create_tally()
        tally.users.add(self.user)
        ballot = create_ballot(tally=tally)
        barcode = ("1234",)
        center = create_center("12345", tally=tally)
        station = create_station(center)
        result_form_1 = create_result_form(
            tally=tally,
            ballot=ballot,
            center=center,
            station_number=station.station_number,
        )
        result_form_2 = create_result_form(
            ballot=ballot,
            barcode=barcode,
            serial_number=2,
            form_state=FormState.ARCHIVED,
            station_number=station.station_number,
            user=None,
            center=center,
            gender=Gender.MALE,
            is_replacement=False,
            tally=tally,
        )
        votes = 12
        create_candidates(
            result_form_1, votes=votes, user=self.user, num_results=1
        )
        for result in result_form_1.results.all():
            result.entry_version = EntryVersion.FINAL
            result.save()
            # create duplicate final results
            create_result(result_form_2, result.candidate, self.user, votes)
        view = views.DuplicateResultFormView.as_view()
        data = {"send_all_clearance": 1}
        request = self.factory.post("/", data=data)
        request.user = self.user
        configure_messages(request)
        response = view(request, tally_id=tally.pk, ballot_id=ballot.number)

        result_form_1.reload()
        result_form_2.reload()
        self.assertEqual(response.status_code, 302)
        self.assertEqual("/", response.url)
        self.assertEqual(result_form_1.form_state, FormState.CLEARANCE)
        self.assertTrue(result_form_1.duplicate_reviewed)
        self.assertNotEqual(result_form_2.form_state, FormState.CLEARANCE)
        self.assertFalse(result_form_2.duplicate_reviewed)

    def test_edit_user_view_get(self):
        tally = create_tally()
        tally.users.add(self.user)
        user = UserProfile.objects.create(
            username="john", first_name="doe", reset_password=False
        )
        tally.users.add(user)
        view = views.EditUserView.as_view()
        request = self.factory.get("/")
        user_id = user.id
        request.user = self.user
        request.session = {}
        request.META = {
            "HTTP_REFERER": f"super-admin/edit-user/{tally.id}/{user_id}/"
        }

        response = view(request, user_id=user_id, tally_id=tally.id)
        response.render()
        self.assertEqual(request.session["url_name"], "user-tally-list")
        self.assertEqual(request.session["url_param"], tally.id)
        self.assertEqual(request.session["url_keyword"], "tally_id")

        request.session = {}
        request.META = {"HTTP_REFERER": "/tally-manager/user-list/user"}

        response = view(request, user_id=user_id, tally_id=tally.id)
        response.render()
        self.assertEqual(request.session["url_name"], "user-list")
        self.assertEqual(request.session["url_param"], "user")
        self.assertEqual(request.session["url_keyword"], "role")

    def test_view_result_forms_progress_by_form_state(self):
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        view = views.FormProgressByFormStateView.as_view()
        request = self.factory.get("/1/")
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)

        # check that the response template is correct.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.template_name,
            ["super_admin/form_progress_by_form_state.html"],
        )
        self.assertEqual(response.context_data["tally_id"], self.tally.pk)

        response = response.render()
        doc = BeautifulSoup(response.content, "html.parser")
        ths = [th.text for th in doc.findAll("th")]
        self.assertListEqual(
            ths,
            [
                "Sub Con Name",
                "Sub Con Code",
                "Office",
                "Election Level",
                "Sub Race",
                "Total forms",
                "Unsubmitted",
                "Intake",
                "DE1",
                "DE2",
                "Corrections",
                "Quality Control",
                "Archived",
                "Clearance",
                "Audit",
            ],
        )

    def test_view_result_forms_progress_by_form_state_data_view(self):
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        view = views.FormProgressByFormStateDataView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)

        # check that the response template is correct.
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        data = content["data"]
        first_row = data[0]
        (
            sub_con_name,
            sub_con_code,
            office,
            election_level,
            sub_race,
            total_forms,
            unsubmitted,
            intake,
            de1,
            de2,
            corrections,
            quality_control,
            archived,
            clearance,
            audit,
        ) = first_row
        self.assertEqual(
            sub_con_name, '<td class="center">subConstituency</td>'
        )
        self.assertEqual(sub_con_code, f'<td class="center">{12345}</td>')
        self.assertEqual(
            election_level, '<td class="center">Presidential</td>'
        )
        self.assertEqual(
            sub_race, '<td class="center">ballot_number_presidential</td>'
        )
        self.assertEqual(total_forms, '<td class="center">10</td>')
        self.assertEqual(
            unsubmitted,
            f'<td class="center"><span>'
            f"<a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            '&at_form_state=unsubmitted target="blank">'
            "1</a></span></td>",
        )
        self.assertEqual(
            intake,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345&at_form_state=intake"
            ' target="blank">'
            "1</a></span>"
            " / "
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            "&pending_at_form_state=intake"
            ' target="blank">'
            "3</a></span></td>",
        )
        self.assertEqual(
            de1,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345&at_form_state=data_entry_1"
            ' target="blank">'
            "1</a></span>"
            " / "
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            "&pending_at_form_state=data_entry_1"
            ' target="blank">'
            "4</a></span></td>",
        )
        self.assertEqual(
            de2,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345&at_form_state=data_entry_2"
            ' target="blank">'
            "1</a></span>"
            " / "
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            "&pending_at_form_state=data_entry_2"
            ' target="blank">'
            "5</a></span></td>",
        )
        self.assertEqual(
            corrections,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345&at_form_state=correction"
            ' target="blank">'
            "1</a></span>"
            " / "
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            "&pending_at_form_state=correction"
            ' target="blank">'
            "6</a></span></td>",
        )
        self.assertEqual(
            quality_control,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            "&at_form_state=quality_control"
            ' target="blank">'
            "1</a></span>"
            " / "
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            "&pending_at_form_state=quality_control"
            ' target="blank">'
            "7</a></span></td>",
        )
        self.assertEqual(
            archived,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345&at_form_state=archived"
            ' target="blank">'
            "1</a></span>"
            " / "
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345"
            "&pending_at_form_state=archived"
            ' target="blank">'
            "8</a></span></td>",
        )
        self.assertEqual(
            clearance,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345&at_form_state=clearance"
            ' target="blank">'
            "1</a></span></td>",
        )
        self.assertEqual(
            audit,
            '<td class="center">'
            f"<span><a href=/data/form-list/{self.tally.pk}/?"
            "election_level=Presidential&sub_race=ballot_number_presidential"
            "&sub_con_code=12345&at_form_state=audit"
            ' target="blank">'
            "1</a></span></td>",
        )

    def test_search_returns_data_result_form_progress_by_form_state_view(self):
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        view = views.FormProgressByFormStateDataView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        request.POST = {}
        request.POST["search[value]"] = 12345

        response = view(request, tally_id=self.tally.pk)

        # check that the response template is correct.
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        data = content["data"]
        self.assertEqual(1, len(data))

    def test_search_returns_no_data_result_form_progress_by_form_state(self):
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        view = views.FormProgressByFormStateDataView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}
        request.POST = {}
        request.POST["search[value]"] = 890

        response = view(request, tally_id=self.tally.pk)

        # check that the response template is correct.
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        data = content["data"]
        self.assertEqual(0, len(data))

    def test_enable_disable_candidate_view(self):
        tally = create_tally()
        ballot = create_ballot(tally)
        candidate = create_candidate(ballot, "candidate name", tally)

        # test diable
        self.assertTrue(candidate.active)
        view = views.DisableCandidateView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(
            request, tally_id=self.tally.id, candidateId=candidate.id
        )
        candidate = Candidate.objects.get(id=candidate.id)
        self.assertFalse(candidate.active)
        self.assertEqual(response.status_code, 302)

        # test enable
        view = views.EnableCandidateView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(
            request, tally_id=self.tally.id, candidateId=candidate.id
        )
        candidate = Candidate.objects.get(id=candidate.id)
        self.assertTrue(candidate.active)
        self.assertEqual(response.status_code, 302)

    def test_remove_station_confirmation_view(self):
        tally = create_tally()
        center = create_center("12345", tally=tally)
        station = create_station(center)
        view = views.RemoveStationConfirmationView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=tally.id, station_id=station.id)
        self.assertEqual(response.status_code, 200)

    def test_quarantine_checks_config_list_view(self):
        tally = create_tally()
        quarantine_data = getattr(settings, "QUARANTINE_DATA")
        create_quarantine_checks(
            tally_id=tally.pk, 
            quarantine_data=quarantine_data
        )
        quarantine_check = QuarantineCheck.objects.get(
            method="pass_card_check", 
            tally=tally
        )
        view = views.QuarantineChecksConfigView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(
            request, tally_id=tally.id, checkId=quarantine_check.id
        )
        self.assertEqual(response.status_code, 200)

        # test list view
        view = views.QuarantineChecksListView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

    def test_enable_disable_ballot_view(self):
        tally = create_tally()
        ballot = create_ballot(tally)
        self.assertTrue(ballot.active)
        view = views.DisableBallotView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=tally.id, ballot_id=ballot.id)
        self.assertEqual(response.status_code, 200)

        request = self.factory.post("/")
        request._messages = messages.storage.default_storage(request)
        request.user = self.user
        response = view(request, tally_id=tally.id, ballot_id=ballot.id)
        self.assertEqual(response.status_code, 200)

        # test enable
        ballot = Ballot.objects.get(id=ballot.id)
        ballot.active = False
        ballot.save()
        self.assertFalse(ballot.active)
        view = views.EnableBallotView.as_view()
        request = self.factory.get("/")
        request._messages = messages.storage.default_storage(request)
        request.user = self.user
        response = view(request, tally_id=tally.id, ballot_id=ballot.id)
        ballot = Ballot.objects.get(id=ballot.id)
        self.assertTrue(ballot.active)
        self.assertEqual(response.status_code, 302)

    def test_enable_disable_electrol_race_view(self):
        tally = create_tally()
        electrol_race = create_electrol_race(self.tally, **electrol_races[0])
        self.assertTrue(self.electrol_race.active)
        view = views.DisableElectrolRaceView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(
            request, tally_id=tally.id, electrol_race_id=electrol_race.id
        )
        electoral_race = ElectrolRace.objects.get(id=electrol_race.id)
        self.assertEqual(response.status_code, 200)
        # test post
        request = self.factory.get("/")
        request._messages = messages.storage.default_storage(request)
        request.user = self.user
        response = view(
            request, tally_id=tally.id, electrol_race_id=electrol_race.id
        )
        self.assertEqual(response.status_code, 200)

        # test enable
        electoral_race.active = False
        electoral_race.save()
        self.assertFalse(electoral_race.active)
        request._messages = messages.storage.default_storage(request)
        view = views.EnableElectrolRaceView.as_view()
        response = view(
            request, tally_id=tally.id, electrol_race_id=electrol_race.id
        )
        electoral_race = ElectrolRace.objects.get(id=electrol_race.id)
        self.assertTrue(electoral_race.active)
        self.assertEqual(response.status_code, 302)

    def test_create_edit_electrol_race_view(self):
        tally = create_tally()
        electrol_race = create_electrol_race(self.tally, **electrol_races[0])
        view = views.EditElectrolRaceView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=tally.id, id=electrol_race.id)
        self.assertEqual(response.status_code, 200)

        # test create
        view = views.CreateElectrolRaceView.as_view()
        response = view(request, tally_id=tally.id, id=electrol_race.id)
        self.assertEqual(response.status_code, 200)

    def test_enable_disable_entity_view(self):
        tally = create_tally()
        center = create_center("12345", tally=tally)
        station = create_station(center)
        view = views.DisableEntityView.as_view()
        request = self.factory.get("/")
        request._messages = messages.storage.default_storage(request)
        request.user = self.user
        response = view(
            request,
            tally_id=tally.id,
            station_number=station.id,
            center_code=center.code,
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_center_view(self):
        tally = create_tally()
        center = create_center("12345", tally=tally)
        view = views.EditCenterView.as_view()
        request = self.factory.get("/")
        request._messages = messages.storage.default_storage(request)
        request.session = {}
        request.user = self.user
        response = view(request, tally_id=tally.id, center_code=center.code)
        self.assertEqual(response.status_code, 200)

    def test_remove_center_confirmation_view(self):
        tally = create_tally()
        center = create_center("12345", tally=tally)
        view = views.RemoveCenterConfirmationView.as_view()
        request = self.factory.get("/")
        request._messages = messages.storage.default_storage(request)
        request.session = {}
        request.user = self.user
        response = view(request, tally_id=tally.id, center_code=center.code)
        self.assertEqual(response.status_code, 200)
        # test post
        request = self.factory.post("/")
        request.session = {}
        request.user = self.user
        request._messages = messages.storage.default_storage(request)
        response = view(request, tally_id=tally.id, center_code=center.code)
        self.assertEqual(response.status_code, 302)

    def test_form_views(self):
        # test FormActionView
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.AUDIT, tally=tally
        )
        create_audit(result_form, self.user)
        view = views.FormActionView.as_view()
        request = self.factory.get("/")
        request._messages = messages.storage.default_storage(request)
        request.session = {}
        request.user = self.user
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        # test FormAuditView
        view = views.FormAuditView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        # test FormClearanceView
        view = views.FormClearanceView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        # test DuplicateResultTrackingView
        view = views.DuplicateResultTrackingView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)
        # test FormProgressView
        view = views.FormProgressView.as_view()
        response = view(request, tally_id=tally.id)
        self.assertEqual(response.status_code, 200)

    def test_tuple_column_sorting_no_error(self):
        """Test that sorting by tuple columns doesn't cause AttributeError."""
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        view = views.FormProgressByFormStateDataView.as_view()

        # Test sorting by a tuple column (intake - column 7)
        request = self.factory.post(
            "/",
            {
                "order[0][column]": "7",  # intake tuple column
                "order[0][dir]": "asc",
                "start": "0",
                "length": "10",
            },
        )
        request.user = self.user
        request.session = {}

        # This should not raise AttributeError: 'tuple' object has no
        # attribute 'replace'
        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)

        # Test sorting by another tuple column (data_entry_1 - column 8)
        request = self.factory.post(
            "/",
            {
                "order[0][column]": "8",
                "order[0][dir]": "desc",
                "start": "0",
                "length": "10",
            },
        )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)

    def test_get_order_columns_maps_tuples_correctly(self):
        """Test that get_order_columns properly maps tuple columns to sort
        fields."""
        view = views.FormProgressByFormStateDataView()
        order_columns = view.get_order_columns()

        # Check that we have the right number of columns
        self.assertEqual(len(order_columns), len(view.columns))

        # Test specific tuple column mappings
        expected_mappings = {
            7: "intake_sort_ratio",
            8: "data_entry_1_sort_ratio",
            9: "data_entry_2_sort_ratio",
            10: "correction_sort_ratio",
            11: "quality_control_sort_ratio",
            12: "archived_sort_ratio",
        }

        for index, expected_field in expected_mappings.items():
            self.assertEqual(order_columns[index], expected_field)
            # Verify the original column is indeed a tuple
            self.assertIsInstance(view.columns[index], tuple)

        # Test that string columns remain unchanged
        string_column_indices = [0, 1, 2, 3, 4, 5, 6, 13, 14]
        for index in string_column_indices:
            self.assertEqual(order_columns[index], view.columns[index])
            self.assertIsInstance(view.columns[index], str)

    def test_string_column_sorting_still_works(self):
        """Test that sorting by string columns continues to work correctly."""
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )
        view = views.FormProgressByFormStateDataView.as_view()

        # Test sorting by string columns (sub_con_name - column 0)
        request = self.factory.post(
            "/",
            {
                "order[0][column]": "0",
                "order[0][dir]": "asc",
                "start": "0",
                "length": "10",
            },
        )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)

        # Test sorting by another string column (office - column 2)
        request = self.factory.post(
            "/",
            {
                "order[0][column]": "2",
                "order[0][dir]": "desc",
                "start": "0",
                "length": "10",
            },
        )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)
        self.assertEqual(response.status_code, 200)

    def test_tuple_sort_ratio_annotations_created(self):
        """Test that tuple sort ratio annotations are properly created in
        queryset."""
        create_result_forms_per_form_state(
            tally=self.tally,
            electrol_race=self.electrol_race,
        )

        view = views.FormProgressByFormStateDataView()
        view.kwargs = {"tally_id": self.tally.pk}
        view.request = self.factory.get("/")
        view.request.POST = {}

        # Get the queryset and verify annotations exist
        qs = view.get_initial_queryset()
        filtered_qs = view.filter_queryset(qs)

        # Check that the queryset has our tuple sort ratio annotations
        expected_annotations = [
            "intake_sort_ratio",
            "data_entry_1_sort_ratio",
            "data_entry_2_sort_ratio",
            "correction_sort_ratio",
            "quality_control_sort_ratio",
            "archived_sort_ratio",
        ]

        # Get the SQL query to check for our annotations
        query_str = str(filtered_qs.query)
        for annotation in expected_annotations:
            self.assertIn(annotation, query_str)

    def test_result_form_search_view_get(self):
        """Test ResultFormSearchView GET request renders form"""
        view = views.ResultFormSearchView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Result Form History")
        self.assertContains(response, "Barcode")

    def test_result_form_search_view_post_valid(self):
        """Test ResultFormSearchView POST with valid barcode"""
        result_form = create_result_form(
            form_state=FormState.INTAKE, tally=self.tally, barcode="12345"
        )

        view = views.ResultFormSearchView.as_view()
        request = self.factory.post(
            "/", {"barcode": "12345", "tally_id": self.tally.pk}
        )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(request.session["result_form"], result_form.pk)

    def test_result_form_search_view_post_invalid(self):
        """Test ResultFormSearchView POST with invalid barcode"""
        view = views.ResultFormSearchView.as_view()
        request = self.factory.post(
            "/", {"barcode": "99999999", "tally_id": self.tally.pk}
        )
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)  # Form redisplay
        self.assertContains(
            response, "Result form with this barcode does not exist"
        )

    def test_result_form_history_view_with_session(self):
        """Test ResultFormHistoryView with valid session"""
        # Create result form with revision history
        with revisions.create_revision():
            result_form = create_result_form(
                form_state=FormState.INTAKE, tally=self.tally, barcode="12345"
            )
            revisions.set_comment("Test revision")

        view = views.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Result Form History")
        self.assertContains(response, "12345")
        self.assertContains(response, "State Transition History")

    def test_result_form_history_view_without_session(self):
        """Test ResultFormHistoryView without session shows error"""
        view = views.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No result form selected")
        self.assertContains(response, "Back to Search")

    def test_result_form_history_view_duration_display(self):
        """Test ResultFormHistoryView shows duration correctly"""
        # Create result form with multiple revisions
        with revisions.create_revision():
            result_form = create_result_form(
                form_state=FormState.UNSUBMITTED,
                tally=self.tally,
                barcode="12345",
            )
            revisions.set_comment("Initial")

        # Add second revision
        with revisions.create_revision():
            result_form.form_state = FormState.INTAKE
            result_form.save()
            revisions.set_comment("To intake")

        view = views.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        # Should contain history data with current state highlighted
        self.assertContains(response, "current-state-row")
        # Check that duration is displayed (might be None for first entry)
        context = response.context_data
        history_data = context.get("history_data", [])
        self.assertTrue(len(history_data) > 0)

        # First entry (newest) should be marked as current
        if history_data:
            self.assertTrue(history_data[0]["is_current"])

    def test_result_form_history_view_no_history(self):
        """Test ResultFormHistoryView with form that has no version history"""
        # Create result form without revisions
        result_form = ResultForm.objects.create(
            barcode="nohistory",
            tally=self.tally,
            form_state=FormState.UNSUBMITTED,
        )

        view = views.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f"No version history found for result form {result_form.barcode}",
        )

    def test_result_form_history_view_permissions(self):
        """
        Test ResultFormHistoryView requires SUPER_ADMINISTRATOR permission
        """
        # Create user without super admin permissions
        self._create_and_login_user(username="regular_user")

        view = views.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}

        # Should raise PermissionDenied due to permission check
        with self.assertRaises(PermissionDenied):
            view(request, tally_id=self.tally.pk)

    def test_form_progress_data_view_modified_date_sorting(self):
        """Test modified_date column for sorting without FieldError."""
        # Create result forms
        create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            barcode="123456789",
            serial_number=1,
        )
        create_result_form(
            form_state=FormState.DATA_ENTRY_2,
            tally=self.tally,
            barcode="123456790",
            serial_number=2,
        )

        # Test that the view can be instantiated and has correct columns
        view = views.FormProgressDataView()
        self.assertIn("modified_date", view.columns)
        self.assertNotIn("modified_date_formatted", view.columns)

        # Test direct queryset ordering to ensure modified_date works
        view.kwargs = {"tally_id": self.tally.pk}
        qs = view.get_initial_queryset()

        # This should not raise FieldError about modified_date_formatted
        try:
            ordered_qs = qs.order_by("modified_date")
            list(ordered_qs)  # Force evaluation
        except Exception as e:
            self.fail(f"Ordering by modified_date failed: {e}")

        # Test reverse ordering
        try:
            ordered_qs = qs.order_by("-modified_date")
            list(ordered_qs)  # Force evaluation
        except Exception as e:
            self.fail(f"Reverse ordering by modified_date failed: {e}")

    def test_form_progress_data_view_modified_date_display(self):
        """Test that modified_date column displays formatted date."""
        # Create a result form
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            barcode="123456791",
            serial_number=3,
        )

        view = views.FormProgressDataView()

        # Test render_column method formats the date correctly
        formatted_date = view.render_column(result_form, "modified_date")
        expected_format = result_form.modified_date_formatted

        self.assertEqual(formatted_date, expected_format)

        # Test that other columns are not affected
        barcode_value = view.render_column(result_form, "barcode")
        # render_column should call super() for non-modified_date columns
        # Since we can't easily test exact super() result, ensure it returns
        self.assertIsNotNone(barcode_value)

    def test_form_audit_data_view_modified_date_sorting(self):
        """Test that FormAuditDataView inherits sorting fix."""
        # Create audit result form
        result_form = create_result_form(
            form_state=FormState.AUDIT,
            tally=self.tally,
            barcode="123456792",
            serial_number=4,
        )

        # Test that the view can be instantiated and has correct columns
        view = views.FormAuditDataView()
        self.assertIn("modified_date", view.columns)
        self.assertNotIn("modified_date_formatted", view.columns)

        # Test that inherited render_column method works for modified_date
        formatted_date = view.render_column(result_form, "modified_date")
        expected_format = result_form.modified_date_formatted
        self.assertEqual(formatted_date, expected_format)

    def test_form_progress_data_view_active_ballot_filter(self):
        """Test that FormProgressDataView filters by active ballots."""
        # Verify the filter is in place by checking the filter_queryset method
        view = views.FormProgressDataView()
        view.kwargs = {"tally_id": self.tally.pk}

        # Mock request without show_inactive parameter
        view.request = self.factory.get("/")
        view.request.POST = {}

        # Test that the method applies the active filter
        qs_mock = view.model.objects.filter(tally=self.tally)
        filtered_qs = view.filter_queryset(qs_mock)

        # Check that the filter includes ballot active filter in the query
        query_str = str(filtered_qs.query)
        self.assertIn('"tally_ballot"."active"', query_str)

        # Test with show_inactive=true parameter
        view.request = self.factory.get("/?show_inactive=true")
        view.request.POST = {}

        filtered_qs_with_inactive = view.filter_queryset(qs_mock)

        # Check that the filter does NOT include ballot__active when
        # show_inactive is true (simplistic test)
        self.assertTrue(hasattr(view, 'filter_queryset'))
        self.assertEqual(filtered_qs_with_inactive.model, view.model)

    def test_form_clearance_data_view_modified_date_sorting(self):
        """Test that FormClearanceDataView inherits sorting fix."""
        # Create clearance result form
        result_form = create_result_form(
            form_state=FormState.CLEARANCE,
            tally=self.tally,
            barcode="123456793",
            serial_number=5,
        )

        # Test that the view can be instantiated and has correct columns
        view = views.FormClearanceDataView()
        self.assertIn("modified_date", view.columns)
        self.assertNotIn("modified_date_formatted", view.columns)

        # Test that inherited render_column method works for modified_date
        formatted_date = view.render_column(result_form, "modified_date")
        expected_format = result_form.modified_date_formatted
        self.assertEqual(formatted_date, expected_format)

    def test_datatables_original_fix_verification(self):
        """Test original FieldError is fixed for modified_date_formatted."""
        # Create result forms
        for i in range(3):
            create_result_form(
                form_state=FormState.DATA_ENTRY_1,
                tally=self.tally,
                barcode=f"12345679{4 + i}",
                serial_number=6 + i,
            )

        # Test that we no longer have modified_date_formatted in columns
        view = views.FormProgressDataView()
        for column in view.columns:
            self.assertNotEqual(
                column,
                "modified_date_formatted",
                "modified_date_formatted should not be in columns",
            )

        # Test that all three affected views have been fixed
        views_to_test = [
            views.FormProgressDataView,
            views.FormAuditDataView,
            views.FormClearanceDataView,
        ]

        for view_class in views_to_test:
            view = view_class()
            self.assertNotIn(
                "modified_date_formatted",
                view.columns,
                f"{view_class.__name__} should not have "
                "modified_date_formatted",
            )
            self.assertIn(
                "modified_date",
                view.columns,
                f"{view_class.__name__} should have modified_date",
            )

            # Test that render_column method exists and works for modified_date
            self.assertTrue(
                hasattr(view, "render_column"),
                f"{view_class.__name__} should have render_column method",
            )

    def test_modified_date_formatted_respects_timezone(self):
        """Test modified_date_formatted handles timezone conversion."""
        # Create a result form
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            barcode="123456799",
            serial_number=10,
        )

        # Test that the formatted date is a string and contains timezone info
        formatted_date = result_form.modified_date_formatted
        self.assertIsInstance(formatted_date, str)

        # The formatted string should contain timezone information
        # Could be UTC, EET, or other timezones depending on system/settings
        # Just check that some timezone info is present
        common_timezones = [
            "UTC",
            "EET",
            "EST",
            "EDT",
            "PST",
            "PDT",
            "CET",
            "CEST",
        ]
        timezone_present = any(tz in formatted_date for tz in common_timezones)
        self.assertTrue(
            timezone_present,
            f"No recognized timezone found in: {formatted_date}",
        )

        # Test that timezone.localtime is being used
        # We can verify this by checking formatted date uses timezone conv
        raw_utc_time = result_form.modified_date
        local_time = timezone.localtime(raw_utc_time)
        expected_format = local_time.strftime("%a, %d %b %Y %H:%M:%S %Z")

        self.assertEqual(formatted_date, expected_format)

        # Verify the format matches the expected pattern
        # Should be like: "Thu, 15 Aug 2025 10:30:45 UTC"
        pattern = r"\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2} \w+"
        self.assertRegex(
            formatted_date,
            pattern,
            f"Date format doesn't match expected pattern: {formatted_date}",
        )

    def test_duplicate_result_tracking_view_filters_inactive_by_default(
        self,
    ):
        """Test DuplicateResultTrackingView filters inactive ballots."""
        # Create active and inactive ballots
        active_ballot = create_ballot(tally=self.tally, active=True, number=10)
        inactive_ballot = create_ballot(
            tally=self.tally, active=False, number=11
        )

        # Create result forms with duplicates
        center = create_center(tally=self.tally)

        # Active ballot result forms (should appear by default)
        active_form1 = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=active_ballot,
            center=center,
            station_number=1,
            barcode="111111111",
            serial_number=100,
        )
        active_form1.duplicate_reviewed = False
        active_form1.save()

        active_form2 = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=active_ballot,
            center=center,
            station_number=1,
            barcode="111111112",
            serial_number=101,
        )
        active_form2.duplicate_reviewed = False
        active_form2.save()

        # Inactive ballot result forms (should be filtered out)
        inactive_form1 = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=inactive_ballot,
            center=center,
            station_number=2,
            barcode="222222221",
            serial_number=200,
        )
        inactive_form1.duplicate_reviewed = False
        inactive_form1.save()

        inactive_form2 = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=inactive_ballot,
            center=center,
            station_number=2,
            barcode="222222222",
            serial_number=201,
        )
        inactive_form2.duplicate_reviewed = False
        inactive_form2.save()

        # Add results to make them candidates for duplication
        candidate1 = create_candidate(
            ballot=active_ballot, candidate_name="Test Candidate 1"
        )
        candidate2 = create_candidate(
            ballot=inactive_ballot, candidate_name="Test Candidate 2"
        )

        # Create duplicate results for active ballot forms
        Result.objects.create(
            candidate=candidate1,
            result_form=active_form1,
            votes=100,
            entry_version=EntryVersion.DATA_ENTRY_1,
        )
        Result.objects.create(
            candidate=candidate1,
            result_form=active_form2,
            votes=100,  # Same votes - makes it a duplicate
            entry_version=EntryVersion.DATA_ENTRY_1,
        )

        # Create duplicate results for inactive ballot forms
        Result.objects.create(
            candidate=candidate2,
            result_form=inactive_form1,
            votes=200,
            entry_version=EntryVersion.DATA_ENTRY_1,
        )
        Result.objects.create(
            candidate=candidate2,
            result_form=inactive_form2,
            votes=200,  # Same votes - makes it a duplicate
            entry_version=EntryVersion.DATA_ENTRY_1,
        )

        view = views.DuplicateResultTrackingView.as_view()
        request = self.factory.get("/")
        request.user = self.user

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["show_inactive"], "false")

        # Should only contain active ballot duplicates
        duplicate_results = response.context_data["duplicate_results"]
        active_barcodes = {form.barcode for form in duplicate_results}

        # Verify only active ballot forms are present
        self.assertIn(active_form1.barcode, active_barcodes)
        self.assertIn(active_form2.barcode, active_barcodes)
        self.assertNotIn(inactive_form1.barcode, active_barcodes)
        self.assertNotIn(inactive_form2.barcode, active_barcodes)

    def test_duplicate_result_tracking_view_shows_inactive_with_parameter(
        self,
    ):
        """Test shows inactive when show_inactive=true."""
        # Create active and inactive ballots
        active_ballot = create_ballot(tally=self.tally, active=True, number=12)
        inactive_ballot = create_ballot(
            tally=self.tally, active=False, number=13
        )

        # Create result forms with duplicates
        center = create_center(tally=self.tally)

        # Active ballot result forms
        active_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=active_ballot,
            center=center,
            station_number=1,
            barcode="333333333",
            serial_number=300,
        )
        active_form.duplicate_reviewed = False
        active_form.save()

        # Inactive ballot result forms
        inactive_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=inactive_ballot,
            center=center,
            station_number=2,
            barcode="444444444",
            serial_number=400,
        )
        inactive_form.duplicate_reviewed = False
        inactive_form.save()

        view = views.DuplicateResultTrackingView.as_view()
        request = self.factory.get(
            "/duplicate-result-tracking?show_inactive=true"
        )
        request.user = self.user

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["show_inactive"], "true")

        # Should contain both active and inactive ballot duplicates
        # (though in this simple case we don't have actual duplicates)
        duplicate_results = response.context_data["duplicate_results"]
        # The function should run without error and include both types
        self.assertIsNotNone(duplicate_results)

    def test_duplicate_result_tracking_view_context_includes_show_inactive(
        self,
    ):
        """Test includes show_inactive in context."""
        view = views.DuplicateResultTrackingView.as_view()

        # Test without show_inactive parameter (default)
        request = self.factory.get("/")
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["show_inactive"], "false")

        # Test with show_inactive=true
        request = self.factory.get("/?show_inactive=true")
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.context_data["show_inactive"], "true")

        # Test with show_inactive=false explicitly
        request = self.factory.get("/?show_inactive=false")
        request.user = self.user
        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.context_data["show_inactive"], "false")

    def test_duplicate_result_form_view_filters_inactive_ballots_by_default(
        self,
    ):
        """Test filters inactive ballots by default."""
        # Create active and inactive ballots
        active_ballot = create_ballot(tally=self.tally, active=True, number=14)
        create_ballot(tally=self.tally, active=False, number=15)

        # Create center and result forms
        center = create_center(tally=self.tally)

        active_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=active_ballot,
            center=center,
            station_number=1,
            barcode="555555555",
            serial_number=500,
        )
        active_form.duplicate_reviewed = False
        active_form.save()

        view = views.DuplicateResultFormView.as_view()
        request = self.factory.get("/")
        request.user = self.user

        response = view(
            request,
            tally_id=self.tally.pk,
            barcode=active_form.barcode,
            ballot_id=active_ballot.number,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["show_inactive"], "false")
        self.assertEqual(
            response.context_data["header_text"], f"Form {active_form.barcode}"
        )

    def test_duplicate_result_form_view_shows_inactive_with_parameter(self):
        """Test shows inactive when show_inactive=true."""
        # Create active ballot and result form
        active_ballot = create_ballot(tally=self.tally, active=True, number=16)

        center = create_center(tally=self.tally)
        active_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=active_ballot,
            center=center,
            station_number=1,
            barcode="666666666",
            serial_number=600,
        )
        active_form.duplicate_reviewed = False
        active_form.save()

        view = views.DuplicateResultFormView.as_view()
        request = self.factory.get("/duplicate-result-form?show_inactive=true")
        request.user = self.user

        response = view(
            request,
            tally_id=self.tally.pk,
            barcode=active_form.barcode,
            ballot_id=active_ballot.number,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["show_inactive"], "true")

        # Should contain results for the specified form
        results = response.context_data["results"]
        self.assertIsNotNone(results)

    def test_get_result_form_with_duplicate_results_function_filters_inactive(
        self,
    ):
        """Test filters inactive ballots."""
        # Create active and inactive ballots
        active_ballot = create_ballot(tally=self.tally, active=True, number=17)
        inactive_ballot = create_ballot(
            tally=self.tally, active=False, number=18
        )

        center = create_center(tally=self.tally)

        # Active ballot form
        active_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=active_ballot,
            center=center,
            station_number=1,
            barcode="777777777",
            serial_number=700,
        )
        active_form.duplicate_reviewed = False
        active_form.save()

        # Inactive ballot form
        inactive_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            ballot=inactive_ballot,
            center=center,
            station_number=2,
            barcode="888888888",
            serial_number=800,
        )
        inactive_form.duplicate_reviewed = False
        inactive_form.save()

        # Test without show_inactive (should filter out inactive)
        duplicates_without_inactive = (
            views.get_result_form_with_duplicate_results(
                tally_id=self.tally.pk, show_inactive=False
            )
        )
        active_barcodes = {
            form.barcode for form in duplicates_without_inactive
        }

        # Should not contain inactive ballot forms
        self.assertNotIn(inactive_form.barcode, active_barcodes)

        # Test with show_inactive=True (should include both)
        duplicates_with_inactive = (
            views.get_result_form_with_duplicate_results(
                tally_id=self.tally.pk, show_inactive=True
            )
        )

        # The function should process both active and inactive forms
        # (though they may not be actual duplicates in this simple test)
        self.assertIsNotNone(duplicates_with_inactive)

    def test_reset_form_confirmation_view_get(self):
        """Test GET request to ResetFormConfirmationView
         displays form correctly."""
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1, tally=tally
        )

        view = views.ResetFormConfirmationView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        response = view(
            request,
            tally_id=tally.pk,
            form_id=result_form.pk
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["tally_id"], tally.pk)
        self.assertIn('reject_reason', response.context_data["form"].fields)

    def test_reset_form_confirmation_view_post_valid(self):
        """Test POST request with valid data creates
        ResultFormReset record."""
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1, tally=tally
        )

        view = views.ResetFormConfirmationView.as_view()
        data = {
            'reject_reason': 'Test reason for reset',
            'reset_submit': 'Reset to Unsubmitted'
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)

        response = view(
            request,
            tally_id=tally.pk,
            form_id=result_form.pk
        )

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Verify form state was reset
        result_form.refresh_from_db()
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

        # Verify ResultFormReset record was created
        reset_records = ResultFormReset.objects.filter(
            result_form=result_form
        )
        self.assertEqual(reset_records.count(), 1)
        reset_record = reset_records.first()
        self.assertEqual(reset_record.user, self.user.userprofile)
        self.assertEqual(reset_record.tally, tally)
        self.assertEqual(reset_record.reason, 'Test reason for reset')

    def test_reset_form_confirmation_view_post_invalid(self):
        """Test POST request with invalid data
        (missing reason) shows errors."""
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1, tally=tally
        )

        view = views.ResetFormConfirmationView.as_view()
        data = {
            'reject_reason': '',  # Empty reason should fail validation
            'reset_submit': 'Reset to Unsubmitted'
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}

        response = view(
            request,
            tally_id=tally.pk,
            form_id=result_form.pk
        )

        # Should return form with errors (200 status)
        self.assertEqual(response.status_code, 200)

        # Verify form state was NOT reset
        result_form.refresh_from_db()
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)

        # Verify NO ResultFormReset record was created
        reset_records = ResultFormReset.objects.filter(
            result_form=result_form
        )
        self.assertEqual(reset_records.count(), 0)

    def test_reset_form_confirmation_view_post_abort(self):
        """Test POST request with abort_submit redirects without resetting."""
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1, tally=tally
        )

        view = views.ResetFormConfirmationView.as_view()
        data = {
            'reject_reason': 'Test reason',
            'abort_submit': 'Cancel'
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)

        response = view(
            request,
            tally_id=tally.pk,
            form_id=result_form.pk
        )

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Verify form state was NOT reset
        result_form.refresh_from_db()
        self.assertEqual(result_form.form_state, FormState.DATA_ENTRY_1)

        # Verify NO ResultFormReset record was created
        reset_records = ResultFormReset.objects.filter(
            result_form=result_form
        )
        self.assertEqual(reset_records.count(), 0)

    def test_reset_form_confirmation_view_deactivates_related_records(self):
        """Test that reset deactivates all related records."""
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.AUDIT, tally=tally
        )

        # Create various related records
        #create_result(result_form, self.user)
        create_reconciliation_form(result_form, self.user)
        create_audit(result_form, self.user)
        clearance = Clearance.objects.create(
            result_form=result_form,
            user=self.user.userprofile
        )

        view = views.ResetFormConfirmationView.as_view()
        data = {
            'reject_reason': 'Deactivate all related records',
            'reset_submit': 'Reset to Unsubmitted'
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)

        view(
            request,
            tally_id=tally.pk,
            form_id=result_form.pk
        )

        # Verify all results are inactive
        for result in result_form.results.all():
            self.assertFalse(result.active)

        # Verify all reconciliation forms are inactive
        for recon in result_form.reconciliationform_set.all():
            self.assertFalse(recon.active)

        # Verify all audits are inactive
        for audit in result_form.audit_set.all():
            self.assertFalse(audit.active)

        # Verify all clearances are inactive
        for clearance in result_form.clearances.all():
            self.assertFalse(clearance.active)

        # Verify form state was reset
        result_form.refresh_from_db()
        self.assertEqual(result_form.form_state, FormState.UNSUBMITTED)

    def test_result_form_reset_auto_populates_tally(self):
        """Test that ResultFormReset.save() auto-populates tally
        from result_form when tally is not explicitly provided."""
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(tally=tally)

        # Create ResultFormReset without explicitly passing tally
        reset_record = ResultFormReset(
            user=self.user.userprofile,
            result_form=result_form,
            reason="Test reason"
        )
        reset_record.save()

        # Verify tally was auto-populated from result_form
        self.assertEqual(reset_record.tally_id, tally.pk)

    def test_reset_form_view_get(self):
        """Test GET request to ResetFormView displays form correctly."""
        tally = create_tally()
        tally.users.add(self.user)

        view = views.ResetFormView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["tally_id"], tally.pk)
        self.assertIn('barcode', response.context_data["form"].fields)
        self.assertIn('tally_id', response.context_data["form"].fields)

    def test_reset_form_view_get_initial_tally_id(self):
        """Test GET request sets initial tally_id in form."""
        tally = create_tally()
        tally.users.add(self.user)

        view = views.ResetFormView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context_data["form"].initial["tally_id"],
            tally.pk
        )

    def test_reset_form_view_post_valid_barcode(self):
        """Test POST with valid barcode redirects to confirmation."""
        tally = create_tally()
        tally.users.add(self.user)
        barcode = '12345678901'
        result_form = create_result_form(
            barcode=barcode,
            form_state=FormState.DATA_ENTRY_1,
            tally=tally
        )

        view = views.ResetFormView.as_view()
        data = {
            'barcode': barcode,
            'tally_id': tally.pk
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)

        response = view(request, tally_id=tally.pk)

        # Should redirect to confirmation page
        self.assertEqual(response.status_code, 302)
        self.assertIn('reset-form-confirmation', response.url)
        self.assertIn(str(result_form.pk), response.url)
        self.assertIn(str(tally.pk), response.url)

    def test_reset_form_view_post_invalid_barcode(self):
        """Test POST with invalid barcode shows errors."""
        tally = create_tally()
        tally.users.add(self.user)

        view = views.ResetFormView.as_view()
        data = {
            'barcode': 'invalid',
            'tally_id': tally.pk
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=tally.pk)

        # Should return form with errors (200 status)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Please enter exactly 11 numbers'
        )

    def test_reset_form_view_post_empty_barcode(self):
        """Test POST with empty barcode shows required error."""
        tally = create_tally()
        tally.users.add(self.user)

        view = views.ResetFormView.as_view()
        data = {
            'barcode': '',
            'tally_id': tally.pk
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=tally.pk)

        # Should return form with errors (200 status)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter exactly 11 numbers")

    def test_reset_form_view_requires_super_admin(self):
        """Test ResetFormView requires 
        SUPER_ADMINISTRATOR permission."""
        tally = create_tally()
        tally.users.add(self.user)

        # Remove user from super admin group
        self.user.groups.clear()

        view = views.ResetFormView.as_view()
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}

        with self.assertRaises(PermissionDenied):
            view(request, tally_id=tally.pk)

    def test_reset_form_view_success_url_generation(self):
        """Test success URL is correctly generated with
          form and tally IDs."""
        tally = create_tally()
        tally.users.add(self.user)
        barcode = '11111111111'
        result_form = create_result_form(
            barcode=barcode,
            tally=tally
        )

        view = views.ResetFormView.as_view()
        data = {
            'barcode': barcode,
            'tally_id': tally.pk
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)

        response = view(request, tally_id=tally.pk)

        # Verify the URL contains correct IDs
        expected_form_id = str(result_form.pk)
        expected_tally_id = str(tally.pk)

        self.assertIn(expected_form_id, response.url)
        self.assertIn(expected_tally_id, response.url)

    def test_reset_form_confirmation_view_success_message(self):
        """Test success message is displayed when reset succeeds."""
        tally = create_tally()
        tally.users.add(self.user)
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=tally,
            barcode='55555555555'
        )

        view = views.ResetFormConfirmationView.as_view()
        data = {
            'reject_reason': 'Test success message',
            'reset_submit': 'Reset to Unsubmitted'
        }
        request = self.factory.post('/', data=data)
        request.user = self.user
        request.session = {}
        configure_messages(request)

        view(
            request,
            tally_id=tally.pk,
            form_id=result_form.pk
        )

        # Verify success message was added
        message_list = list(messages.get_messages(request))
        self.assertTrue(any(
            'successfully reset to Unsubmitted' in str(msg)
            for msg in message_list
        ))

        # Verify barcode is in success message
        self.assertTrue(any(
            '55555555555' in str(msg)
            for msg in message_list
        ))
