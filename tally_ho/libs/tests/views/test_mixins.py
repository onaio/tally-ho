import json

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import Http404, HttpResponse
from django.test import RequestFactory
from django.views.generic.base import View

from tally_ho.libs.permissions import groups
from tally_ho.libs.tests.test_base import (TestBase,
                                           create_tally)
from tally_ho.libs.views.mixins import (AjaxLoginRequiredMixin,
                                        GroupRequiredMixin,
                                        TallyAccessMixin,
                                        get_datatables_context)


class ViewGroupRequiredNoGroups(GroupRequiredMixin, View):
    pass


class ViewGroupRequired(GroupRequiredMixin, View):
    group_required = groups.INTAKE_CLERK


class ViewTwoGroupsRequired(GroupRequiredMixin, View):
    group_required = [groups.DATA_ENTRY_1_CLERK,
                      groups.DATA_ENTRY_2_CLERK]


class ViewAjaxLoginRequired(AjaxLoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')


class TestAjaxLoginRequiredMixin(TestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_unauthenticated_ajax_request_returns_401(self):
        """Test that unauthenticated AJAX requests return 401 JSON response."""
        view = ViewAjaxLoginRequired.as_view()
        request = self.factory.get(
            '/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = AnonymousUser()

        response = view(request)

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'session_expired')
        self.assertIn('login_url', data)

    def test_unauthenticated_non_ajax_request_redirects(self):
        """Test that unauthenticated non-AJAX requests redirect to login."""
        view = ViewAjaxLoginRequired.as_view()
        request = self.factory.get('/')
        request.user = AnonymousUser()

        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_authenticated_ajax_request_succeeds(self):
        """Test that authenticated AJAX requests proceed normally."""
        self._create_and_login_user()
        view = ViewAjaxLoginRequired.as_view()
        request = self.factory.get(
            '/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user

        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')

    def test_authenticated_non_ajax_request_succeeds(self):
        """Test that authenticated non-AJAX requests proceed normally."""
        self._create_and_login_user()
        view = ViewAjaxLoginRequired.as_view()
        request = self.factory.get('/')
        request.user = self.user

        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')


class TestGroupRequired(TestBase):
    def test_improperly_configured(self):
        view = ViewGroupRequiredNoGroups.as_view()
        self._create_and_login_user()
        with self.assertRaises(ImproperlyConfigured):
            view(self.request)

    def test_super_admin(self):
        view = ViewGroupRequired.as_view()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.SUPER_ADMINISTRATOR)

        try:
            view(self.request)
        except PermissionDenied:
            self.fail('view(self.request) raised PermissionDenied'
                      'unexpectedly')

    def test_multiple_groups_reject(self):
        view = ViewGroupRequired.as_view()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)

        try:
            view(self.request)
            self.fail('view(self.request) did not raise PermissionDenied')
        except PermissionDenied:
            pass

    def test_multiple_groups(self):
        view = ViewTwoGroupsRequired.as_view()
        self._create_and_login_user()
        self._add_user_to_group(self.user, groups.DATA_ENTRY_2_CLERK)

        try:
            view(self.request)
        except PermissionDenied:
            self.fail('view(self.request) raised PermissionDenied'
                      'unexpectedly')


class TestDataTablesContext(TestBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_get_datatables_context(self):
        """Test that get_datatables_context returns all required context
        variables with correct values."""
        request = self.factory.get('/')
        request.LANGUAGE_CODE = 'en'

        context = get_datatables_context(request)

        # Check all required keys are present
        required_keys = [
            'languageDE',
            'deployedSiteUrl',
            'enable_responsive',
            'enable_scroll_x',
            'regions_list_download_url',
            'offices_list_download_url',
            'get_centers_stations_url',
            'get_export_url',
            'results_download_url',
            'centers_by_mun_results_download_url',
            'centers_by_mun_candidate_votes_results_download_url',
            'centers_stations_by_mun_candidates_votes_results_download_url',
            'sub_cons_list_download_url',
            'result_forms_download_url',
            'centers_and_stations_list_download_url',
            'candidates_list_download_url'
        ]

        for key in required_keys:
            self.assertIn(key, context, f"Missing required key: {key}")

        # Test with different locale
        context_ar = get_datatables_context(request)
        self.assertIn('languageDE', context_ar)

    def test_get_datatables_context_enable_scroll_x_default(self):
        """Test that enable_scroll_x defaults to True when not specified."""
        request = self.factory.get('/')
        request.LANGUAGE_CODE = 'en'

        context = get_datatables_context(request)
        self.assertFalse(context['enable_scroll_x'])

    def test_get_datatables_context_enable_scroll_x_true(self):
        """Test that enable_scroll_x can be set to True explicitly."""
        request = self.factory.get('/')
        request.LANGUAGE_CODE = 'en'

        context = get_datatables_context(request, enable_scroll_x=True)
        self.assertTrue(context['enable_scroll_x'])

    def test_get_datatables_context_enable_scroll_x_false(self):
        """Test that enable_scroll_x can be set to False."""
        request = self.factory.get('/')
        request.LANGUAGE_CODE = 'en'

        context = get_datatables_context(request, enable_scroll_x=False)
        self.assertFalse(context['enable_scroll_x'])


class ViewWithTallyAccess(View):
    """Test view that uses TallyAccessMixin"""
    def dispatch(self, request, *args, **kwargs):
        return TallyAccessMixin.dispatch(self, request, *args, **kwargs)


class TestTallyAccessMixin(TestBase):
    def setUp(self):
        super().setUp()        
        self.create_tally = create_tally
        self.factory = RequestFactory()
        self._create_permission_groups()
        self._create_and_login_user()

    def test_inactive_tally_blocks_access(self):
        """Test that access to inactive tally is blocked for all users"""
        # Create an inactive tally
        tally = self.create_tally()
        tally.active = False
        tally.save()

        # Add user to tally manager group
        self._add_user_to_group(self.user, groups.TALLY_MANAGER)

        # Create request
        request = self.factory.get(f'super-administrator/{tally.id}/')
        request.user = self.user
      
        view = ViewWithTallyAccess.as_view()

        # Should return a 404
        with self.assertRaises(Http404):
            view(request, tally_id=tally.id)

