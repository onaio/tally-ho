from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from libya_tally.apps.tally.forms.login_form import LoginForm
from libya_tally.apps.tally.views import archive, audit, clearance,\
    corrections, data_entry_clerk, home, intake_clerk, quality_control,\
    super_admin
from libya_tally.apps.tally.views.reports import overview

admin.autodiscover()

accounts_urls = patterns(
    '',
    url(r'^login/$', auth_views.login,
        {'template_name': 'registration/login.html',
         'authentication_form': LoginForm},
        name='login'),
    url(r'^logout/$', auth_views.logout, {'next_page': '/'}, name='logout'),
)

handler403 = 'libya_tally.apps.tally.views.home.permission_denied'
handler404 = 'libya_tally.apps.tally.views.home.not_found'
handler400 = 'libya_tally.apps.tally.views.home.bad_request'
handler500 = 'libya_tally.apps.tally.views.home.server_error'

urlpatterns = patterns(
    '',
    url(r'^$', home.HomeView.as_view(), name='home'),
    url(r'^locale$', home.LocaleView.as_view(), name='home-locale'),

    url(r'^super-administrator$',
        super_admin.DashboardView.as_view(), name='super-administrator'),
    url(r'^super-administrator/center-list$',
        super_admin.CenterListView.as_view(),
        name='center-list'),
    url(r'^super-administrator/center-list-data$',
        super_admin.CenterListDataView.as_view(),
        name='center-list-data'),
    url(r'^super-administrator/form-list$',
        super_admin.FormListView.as_view(),
        name='form-list'),
    url(r'^super-administrator/form-list-data$',
        super_admin.FormListDataView.as_view(),
        name='form-list-data'),
    url(r'^super-administrator/form-progress$',
        super_admin.FormProgressView.as_view(),
        name='form-progress'),
    url(r'^super-administrator/form-action-list$',
        super_admin.FormActionView.as_view(),
        name='form-action-view'),
    url(r'^super-administrator/form-progress-data$',
        super_admin.FormProgressDataView.as_view(),
        name='form-progress-data'),

    url(r'^data-entry$', data_entry_clerk.DataEntryView.as_view(),
        name='data-entry-clerk'),
    url(r'^data-entry/enter-center-details$',
        data_entry_clerk.CenterDetailsView.as_view(),
        name='data-entry-enter-center-details'),
    url(r'^data-entry/check-center-details$',
        data_entry_clerk.CheckCenterDetailsView.as_view(),
        name='data-entry-check-center-details'),
    url(r'^data-entry/enter-results',
        data_entry_clerk.EnterResultsView.as_view(),
        name='enter-results'),

    url(r'^intake/center-details$', intake_clerk.CenterDetailsView.as_view(),
        name='intake-clerk'),
    url(r'^intake/enter-center', intake_clerk.EnterCenterView.as_view(),
        name='intake-enter-center'),
    url(r'^intake/check-center-details$',
        intake_clerk.CheckCenterDetailsView.as_view(),
        name='check-center-details'),
    url(r'^intake/printcover$',
        intake_clerk.PrintCoverView.as_view(),
        name='intake-printcover'),
    url(r'^intake/clearance$',
        intake_clerk.ClearanceView.as_view(),
        name='intake-clearance'),
    url(r'^intake/intaken',
        intake_clerk.ConfirmationView.as_view(),
        name='intaken'),

    url(r'^quality-control/home$',
        quality_control.QualityControlView.as_view(),
        name='quality-control-clerk'),
    url(r'^quality-control/dashboard$',
        quality_control.QualityControlDashboardView.as_view(),
        name='quality-control-dashboard'),
    url(r'^quality-control/reject',
        TemplateView.as_view(
            template_name='tally/quality_control/reject.html'),
        name='quality-control-reject'),

    url(r'^corrections$',
        corrections.CorrectionView.as_view(),
        name='corrections-clerk'),
    url(r'^corrections/match$',
        corrections.CorrectionMatchView.as_view(),
        name='corrections-match'),
    url(r'^corrections/required',
        corrections.CorrectionRequiredView.as_view(),
        name='corrections-required'),

    url(r'^archive$',
        archive.ArchiveView.as_view(),
        name='archive-clerk'),
    url(r'^archive/print$',
        archive.ArchivePrintView.as_view(),
        name='archive-print'),

    url(r'^audit$',
        audit.DashboardView.as_view(),
        name='audit'),
    url(r'^audit/new',
        audit.CreateAuditView.as_view(),
        name='audit-new'),
    url(r'^audit/print',
        audit.PrintCoverView.as_view(),
        name='audit-print'),
    url(r'^audit/review$',
        audit.ReviewView.as_view(),
        name='audit-review'),

    url(r'^clearance$',
        clearance.DashboardView.as_view(),
        name='clearance'),
    url(r'^clearance/new',
        clearance.NewFormView.as_view(),
        name='clearance-new'),
    url(r'^clearance/print',
        clearance.PrintCoverView.as_view(),
        name='clearance-print'),
    url(r'^clearance/review$',
        clearance.ReviewView.as_view(),
        name='clearance-review'),

    url(r'^reports/internal/overview$',
        overview.OverviewReportView.as_view(),
        name='reports-overview'),

    url(r'^accounts/', include(accounts_urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^tracking/', include('tracking.urls')),
    url(r'^djangojs/', include('djangojs.urls')),
)
