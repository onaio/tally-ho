from django.urls import include, path, re_path
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from tally_ho.apps.tally.forms.login_form import LoginForm
from tally_ho.apps.tally.forms.password_change import PasswordChangeForm
from tally_ho.apps.tally.views import audit, clearance,\
    corrections, data_entry, home, intake, quality_control,\
    super_admin, profile
from tally_ho.apps.tally.views.data import center_list_view, form_list_view
from tally_ho.apps.tally.views.reports import offices
from tally_ho.apps.tally.views.reports import races

admin.autodiscover()

accounts_urls = [
    path('login/',
         profile.login,
         {
             'template_name': 'registration/login.html',
             'authentication_form': LoginForm
         },
         name='login'),
    path('password_change/',
         auth_views.PasswordChangeView.as_view(),
         {
             'password_change_form': PasswordChangeForm,
             'post_change_redirect': '/'},
         name='password_change'),
    path('password_change/done/',
         auth_views.PasswordChangeDoneView.as_view(),
         name='password_change_done'),
    path('logout/',
         auth_views.LogoutView.as_view(),
         {'next_page': '/'},
         name='logout'),
]

handler403 = 'tally_ho.apps.tally.views.home.permission_denied'
handler404 = 'tally_ho.apps.tally.views.home.not_found'
handler400 = 'tally_ho.apps.tally.views.home.bad_request'
handler500 = 'tally_ho.apps.tally.views.home.server_error'

urlpatterns = [
    path('', home.HomeView.as_view(), name='home'),
    path('locale', home.LocaleView.as_view(), name='home-locale'),

    path('data/center-list',
         center_list_view.CenterListView.as_view(),
         name='center-list'),
    path('data/center-list-data',
         center_list_view.CenterListDataView.as_view(),
         name='center-list-data'),
    path('data/form-list',
         form_list_view.FormListView.as_view(),
         name='form-list'),
    re_path('data/form-list/(?P<state>.*)/',
            form_list_view.FormListView.as_view(),
            name='form-list'),
    path('data/form-list-data',
         form_list_view.FormListDataView.as_view(),
         name='form-list-data'),
    re_path('data/form-not-received.(?P<format>(csv))',
            form_list_view.FormNotReceivedListView.as_view(),
            name='form-not-received-view'),
    path('data/form-not-received',
         form_list_view.FormNotReceivedListView.as_view(),
         name='form-not-received-view'),
    path('data/form-not-received-data',
         form_list_view.FormNotReceivedDataView.as_view(),
         name='form-not-received-data'),
    re_path('data/forms-for-race/(?P<ballot>.*)/',
            form_list_view.FormsForRaceView.as_view(),
            name='forms-for-race'),
    re_path('data/forms-for-race-data/(?P<ballot>.*)/',
            form_list_view.FormListDataView.as_view(),
            name='forms-for-race-data'),

    path('super-administrator',
         super_admin.DashboardView.as_view(), name='super-administrator'),
    path('super-administrator/form-progress',
         super_admin.FormProgressView.as_view(),
         name='form-progress'),
    path('super-administrator/form-duplicates',
         super_admin.FormDuplicatesView.as_view(),
         name='form-duplicates'),
    path('super-administrator/form-action-list',
         super_admin.FormActionView.as_view(),
         name='form-action-view'),
    path('super-administrator/form-progress-data',
         super_admin.FormProgressDataView.as_view(),
         name='form-progress-data'),
    path('super-administrator/form-duplicates-data',
         super_admin.FormDuplicatesDataView.as_view(),
         name='form-duplicates-data'),
    re_path('super-administrator/results-(?P<report>.*).csv',
            super_admin.ResultExportView.as_view(),
            name='result-export'),
    path('super-administrator/results',
         super_admin.ResultExportView.as_view(),
         name='result-export'),
    path('super-administrator/remove-centre',
         super_admin.RemoveCenterView.as_view(),
         name='remove-center'),
    path('super-administrator/remove-station',
         super_admin.RemoveStationView.as_view(),
         name='remove-station'),

    path('data-entry', data_entry.DataEntryView.as_view(),
         name='data-entry'),
    path('data-entry/enter-center-details',
         data_entry.CenterDetailsView.as_view(),
         name='data-entry-enter-center-details'),
    path('data-entry/enter-results',
         data_entry.EnterResultsView.as_view(),
         name='enter-results'),
    path('data-entry/success',
         data_entry.ConfirmationView.as_view(),
         name='data-entry-success'),

    path('intake/center-details',
         intake.CenterDetailsView.as_view(),
         name='intake'),
    path('intake/enter-center',
         intake.EnterCenterView.as_view(),
         name='intake-enter-center'),
    path('intake/check-center-details',
         intake.CheckCenterDetailsView.as_view(),
         name='check-center-details'),
    path('intake/printcover',
         intake.PrintCoverView.as_view(),
         name='intake-printcover'),
    path('intake/clearance',
         intake.ClearanceView.as_view(),
         name='intake-clearance'),
    path('intake/intaken',
         intake.ConfirmationView.as_view(),
         name='intaken'),

    path('quality-control/home',
         quality_control.QualityControlView.as_view(),
         name='quality-control'),
    path('quality-control/dashboard',
         quality_control.QualityControlDashboardView.as_view(),
         name='quality-control-dashboard'),
    path('quality-control/reject',
         TemplateView.as_view(
             template_name='tally/quality_control/reject.html'),
         name='quality-control-reject'),
    path('quality-control/print',
         quality_control.PrintView.as_view(),
         name='quality-control-print'),
    path('quality-control/success',
         quality_control.ConfirmationView.as_view(),
         name='quality-control-success'),

    path('corrections',
         corrections.CorrectionView.as_view(),
         name='corrections'),
    path('corrections/match',
         corrections.CorrectionMatchView.as_view(),
         name='corrections-match'),
    path('corrections/required',
         corrections.CorrectionRequiredView.as_view(),
         name='corrections-required'),
    path('corrections/success',
         corrections.ConfirmationView.as_view(),
         name='corrections-success'),

    path('audit',
         audit.DashboardView.as_view(),
         name='audit'),
    path('audit/new',
         audit.CreateAuditView.as_view(),
         name='audit-new'),
    path('audit/print',
         audit.PrintCoverView.as_view(),
         name='audit-print'),
    path('audit/review',
         audit.ReviewView.as_view(),
         name='audit-review'),

    path('clearance',
         clearance.DashboardView.as_view(),
         name='clearance'),
    path('clearance/new',
         clearance.NewFormView.as_view(),
         name='clearance-new'),
    path('clearance/print',
         clearance.PrintCoverView.as_view(),
         name='clearance-print'),
    path('clearance/review',
         clearance.ReviewView.as_view(),
         name='clearance-review'),
    path('clearance/create',
         clearance.CreateClearanceView.as_view(),
         name='clearance-create'),

    path('reports/internal/offices',
         offices.OfficesReportView.as_view(),
         name='reports-offices'),
    path('reports/internal/race',
         races.RacesReportView.as_view(),
         name='reports-races'),

    path('operation-not-allowed',
         home.suspicious_error,
         name='suspicious-error'),

    path('accounts/', include(accounts_urls)),
    path('admin/', admin.site.urls),
    path('tracking/', include('tracking.urls')),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
