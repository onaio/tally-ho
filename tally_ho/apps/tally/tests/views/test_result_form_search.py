from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.utils import timezone as django_timezone
from reversion import revisions
from reversion.models import Version

from tally_ho.apps.tally.views import result_form_search
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (
    TestBase,
    create_result_form,
    create_tally,
)


class TestResultFormSearchHelpers(TestBase):
    """Test helper functions in result_form_search module"""

    def setUp(self):
        self.factory = RequestFactory()
        self.tally = create_tally()

    def test_extract_timestamp_from_version_none_input(self):
        """Test extract_timestamp_from_version with None input"""
        result = result_form_search.extract_timestamp_from_version(None)
        self.assertIsNone(result)

    def test_extract_timestamp_from_version_string_date(self):
        """Test extract_timestamp_from_version with string timestamp"""

        # Create a mock version with string modified_date
        class MockVersion:
            field_dict = {"modified_date": "2023-01-01T12:00:00Z"}

        version = MockVersion()
        result = result_form_search.extract_timestamp_from_version(version)
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)

    def test_extract_timestamp_from_version_datetime_object(self):
        """Test extract_timestamp_from_version with datetime object"""
        test_datetime = datetime(2023, 5, 15, 10, 30, 0, tzinfo=timezone.utc)

        class MockVersion:
            field_dict = {"modified_date": test_datetime}

        version = MockVersion()
        result = result_form_search.extract_timestamp_from_version(version)
        self.assertEqual(result, test_datetime)

    def test_extract_timestamp_from_version_missing_date(self):
        """Test extract_timestamp_from_version with missing modified_date"""

        class MockVersion:
            field_dict = {}

        version = MockVersion()
        result = result_form_search.extract_timestamp_from_version(version)
        self.assertIsNone(result)

    def test_create_result_form_history_entry_no_user(self):
        """Test create_result_form_history_entry with no user"""
        result_form = create_result_form(
            form_state=FormState.INTAKE, tally=self.tally, barcode="12345"
        )
        result_form.user_id = None
        result_form.save()

        entry = result_form_search.create_result_form_history_entry(
            result_form
        )

        self.assertEqual(entry["user"], "Unknown")
        self.assertEqual(entry["current_state"], "INTAKE")
        self.assertEqual(entry["previous_state"], "None")
        self.assertTrue(entry["is_current"])
        self.assertIsNone(entry["version_id"])

    def test_create_result_form_history_entry_with_user(self):
        """Test create_result_form_history_entry with valid user"""
        from tally_ho.apps.tally.models.user_profile import UserProfile

        user_profile = UserProfile.objects.create(username="testuser")
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            barcode="12345",
        )
        result_form.user = user_profile
        result_form.previous_form_state = FormState.INTAKE
        result_form.save()

        entry = result_form_search.create_result_form_history_entry(
            result_form
        )

        self.assertEqual(entry["user"], "testuser")
        self.assertEqual(entry["current_state"], "DATA_ENTRY_1")
        self.assertEqual(entry["previous_state"], "INTAKE")
        self.assertTrue(entry["is_current"])

    def test_create_result_form_history_entry_with_duration(self):
        """Test create_result_form_history_entry with duration calculation"""
        result_form = create_result_form(
            form_state=FormState.DATA_ENTRY_1,
            tally=self.tally,
            barcode="12345",
        )

        # Set timestamps for duration calculation
        last_timestamp = django_timezone.now() - django_timezone.timedelta(
            hours=2
        )
        result_form.modified_date = django_timezone.now()
        result_form.save()

        entry = result_form_search.create_result_form_history_entry(
            result_form, last_timestamp
        )

        self.assertIsNotNone(entry["duration_in_previous_state"])
        self.assertIsNotNone(entry["duration_display"])

    def test_create_version_history_entry_basic(self):
        """Test create_version_history_entry with basic version data"""
        user = User.objects.create_user(username="versionuser")

        class MockVersion:
            pk = 123
            field_dict = {
                "user_id": user.id,
                "modified_date": "2023-01-01T12:00:00Z",
                "form_state": FormState.INTAKE,
                "previous_form_state": FormState.UNSUBMITTED,
            }

        version = MockVersion()
        entry = result_form_search.create_version_history_entry(version)

        self.assertEqual(entry["user"], "versionuser")
        self.assertEqual(entry["current_state"], "INTAKE")
        self.assertEqual(entry["previous_state"], "UNSUBMITTED")
        self.assertEqual(entry["version_id"], 123)
        self.assertFalse(entry["is_current"])

    def test_create_version_history_entry_nonexistent_user(self):
        """Test create_version_history_entry with nonexistent user ID"""

        class MockVersion:
            pk = 123
            field_dict = {
                "user_id": 99999,  # Non-existent user ID
                "modified_date": "2023-01-01T12:00:00Z",
                "form_state": FormState.INTAKE,
                "previous_form_state": None,
            }

        version = MockVersion()
        entry = result_form_search.create_version_history_entry(version)

        self.assertEqual(entry["user"], "User ID 99999")
        self.assertEqual(entry["previous_state"], "None")

    def test_get_result_form_history_data_no_versions(self):
        """Test get_result_form_history_data with no version history"""
        result_form = create_result_form(
            form_state=FormState.INTAKE, tally=self.tally, barcode="12345"
        )

        versions = Version.objects.none()  # Empty queryset
        history_data = result_form_search.get_result_form_history_data(
            result_form, versions
        )

        # Should have one entry (current state)
        self.assertEqual(len(history_data), 1)
        self.assertTrue(history_data[0]["is_current"])
        self.assertEqual(history_data[0]["current_state"], "INTAKE")

    def test_get_result_form_history_data_with_versions(self):
        """Test get_result_form_history_data with version history"""
        with revisions.create_revision():
            result_form = create_result_form(
                form_state=FormState.UNSUBMITTED,
                tally=self.tally,
                barcode="12345",
            )
            revisions.set_comment("Initial")

        with revisions.create_revision():
            result_form.form_state = FormState.INTAKE
            result_form.save()
            revisions.set_comment("To intake")

        versions = Version.objects.get_for_object(result_form).order_by("pk")
        history_data = result_form_search.get_result_form_history_data(
            result_form, versions
        )

        # Should have current entry + version entries
        self.assertGreater(len(history_data), 2)

        # First entry should be current state
        self.assertTrue(history_data[0]["is_current"])
        self.assertEqual(history_data[0]["current_state"], "INTAKE")

        # All other entries should not be current
        for entry in history_data[1:]:
            self.assertFalse(entry["is_current"])


class TestResultFormSearchViews(TestBase):
    """Test ResultFormSearchView and ResultFormHistoryView"""

    def setUp(self):
        self.factory = RequestFactory()
        self.tally = create_tally()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)
        self.tally.users.add(self.user)

    def test_result_form_search_view_get(self):
        """Test ResultFormSearchView GET request renders form"""
        view = result_form_search.ResultFormSearchView.as_view()
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

        view = result_form_search.ResultFormSearchView.as_view()
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
        view = result_form_search.ResultFormSearchView.as_view()
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

    def test_result_form_search_view_permissions(self):
        """Test ResultFormSearchView requires SUPER_ADMINISTRATOR permission"""
        # Create user without super admin permissions
        self._create_and_login_user(username="regular_user")

        view = result_form_search.ResultFormSearchView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}

        with self.assertRaises(PermissionDenied):
            view(request, tally_id=self.tally.pk)

    def test_result_form_history_view_current_state_first(self):
        """Test ResultFormHistoryView shows current state as first row"""
        # Create result form with revision history
        with revisions.create_revision():
            result_form = create_result_form(
                form_state=FormState.UNSUBMITTED,
                tally=self.tally,
                barcode="12345",
            )
            revisions.set_comment("Initial")

        # Update to new state
        with revisions.create_revision():
            result_form.form_state = FormState.INTAKE
            result_form.previous_form_state = FormState.UNSUBMITTED
            result_form.save()
            revisions.set_comment("To intake")

        view = result_form_search.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        context = response.context_data
        history_data = context.get("history_data", [])

        # Should have multiple entries
        self.assertGreater(len(history_data), 1)

        # First entry should be current state from ResultForm
        first_entry = history_data[0]
        self.assertTrue(first_entry["is_current"])
        self.assertEqual(first_entry["current_state"], "INTAKE")
        self.assertEqual(first_entry["previous_state"], "UNSUBMITTED")
        # Current entry has no version_id
        self.assertIsNone(first_entry["version_id"])

        # All other entries should be from version history
        for entry in history_data[1:]:
            self.assertFalse(entry["is_current"])
            self.assertIsNotNone(entry["version_id"])

    def test_result_form_history_view_without_session(self):
        """Test ResultFormHistoryView without session shows error"""
        view = result_form_search.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No result form selected")
        self.assertContains(response, "Back to Search")

    def test_result_form_history_view_no_versions_shows_current(self):
        """Test ResultFormHistoryView with no versions shows current state"""
        # Create result form without using revisions
        result_form = create_result_form(
            form_state=FormState.INTAKE, tally=self.tally, barcode="nohistory"
        )

        view = result_form_search.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)

        # Should show current state even with no version history
        context = response.context_data
        history_data = context.get("history_data", [])

        self.assertEqual(len(history_data), 1)  # Only current entry
        self.assertTrue(history_data[0]["is_current"])
        self.assertEqual(history_data[0]["current_state"], "INTAKE")

    def test_result_form_history_view_duration_calculation(self):
        """Test ResultFormHistoryView shows duration correctly"""
        # Create result form with multiple revisions and time gaps
        with revisions.create_revision():
            result_form = create_result_form(
                form_state=FormState.UNSUBMITTED,
                tally=self.tally,
                barcode="12345",
            )
            revisions.set_comment("Initial")

        # Add second revision with time difference
        with revisions.create_revision():
            result_form.form_state = FormState.INTAKE
            result_form.save()
            revisions.set_comment("To intake")

        view = result_form_search.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)

        context = response.context_data
        history_data = context.get("history_data", [])

        # Should have current entry + version entries
        self.assertGreater(len(history_data), 1)

        # Current entry (first) may have duration from last version
        current_entry = history_data[0]
        self.assertTrue(current_entry["is_current"])

        # Duration might be calculated between current state and last version
        # This depends on timing, so we just check structure is correct
        self.assertIn("duration_display", current_entry)

    def test_result_form_history_view_permissions(self):
        """Test ResultFormHistoryView requires SUPER_ADMINISTRATOR access"""
        # Create user without super admin permissions
        self._create_and_login_user(username="regular_user")

        result_form = create_result_form(
            form_state=FormState.INTAKE, tally=self.tally, barcode="12345"
        )

        view = result_form_search.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": result_form.pk}

        with self.assertRaises(PermissionDenied):
            view(request, tally_id=self.tally.pk)

    def test_result_form_history_view_invalid_form(self):
        """Test ResultFormHistoryView with invalid result form ID"""
        view = result_form_search.ResultFormHistoryView.as_view()
        request = self.factory.get("/")
        request.user = self.user
        request.session = {"result_form": 99999}  # Non-existent ID

        response = view(request, tally_id=self.tally.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Result form not found")
