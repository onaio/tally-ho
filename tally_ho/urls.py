from django.urls import include, path, re_path
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.views.static import serve

from tally_ho.apps.tally.forms.login_form import LoginForm
from tally_ho.apps.tally.forms.password_change import PasswordChangeForm
from tally_ho.apps.tally.views import audit, clearance,\
    corrections, data_entry, home, intake, quality_control,\
    super_admin, profile, tally_manager
from tally_ho.apps.tally.views.data import center_list_view, form_list_view,\
    candidate_list_view, race_list_view, user_list_view, tally_list_view
from tally_ho.apps.tally.views.reports import administrative_areas_reports
from tally_ho.apps.tally.views.reports import offices
from tally_ho.apps.tally.views.reports import races
from tally_ho.apps.tally.views.reports import staff_performance_metrics
from tally_ho.apps.tally.views.reports import station_progress_report
from tally_ho.apps.tally.views.reports import candidate_list_by_votes
from tally_ho.apps.tally.views.reports import overall_votes
from tally_ho.apps.tally.views.reports import votes_per_candidate

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
         auth_views.PasswordChangeView.as_view(
             form_class=PasswordChangeForm),
         name='password_change'),
    path('password_change/done/',
         auth_views.PasswordChangeDoneView.as_view(),
         name='password_change_done'),
    path('logout/',
         auth_views.LogoutView.as_view(),
         {'next_page': settings.LOGOUT_REDIRECT_URL},
         name='logout'),
]

handler403 = 'tally_ho.apps.tally.views.home.permission_denied'
handler404 = 'tally_ho.apps.tally.views.home.not_found'
handler400 = 'tally_ho.apps.tally.views.home.bad_request'
handler500 = 'tally_ho.apps.tally.views.home.server_error'

urlpatterns = [
    path('', home.HomeView.as_view(), name='home'),
    path('locale', home.LocaleView.as_view(), name='home-locale'),
    path('not-tally', home.NoTallyView.as_view(), name='home-no-tally'),

    re_path(r'^media/(?P<path>.*)$', serve,
            {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^data/center-list/(?P<tally_id>(\d+))/$',
            center_list_view.CenterListView.as_view(),
            name='center-list'),
    re_path(r'^data/center-list/(?P<tally_id>(\d+))/(?P<format>(csv))/$',
            center_list_view.CenterListView.as_view(),
            name='center-list-csv'),
    re_path(r'^data/center-list-data/(?P<tally_id>(\d+))/$',
            center_list_view.CenterListDataView.as_view(),
            name='center-list-data'),
    re_path(r'^data/center-list/(?P<tally_id>(\d+))/(?P<region_id>(\d+))/$',
            center_list_view.CenterListView.as_view(),
            name='center-and-stations-in-audit-list'),
    re_path(r'^data/center-list-data/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/$',
            center_list_view.CenterListDataView.as_view(),
            name='center-list-data'),
    re_path(r'^data/center-list/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/$',
            center_list_view.CenterListView.as_view(),
            name='center-and-stations-in-audit-list'),
    re_path(r'^data/center-list-data/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/$',
            center_list_view.CenterListDataView.as_view(),
            name='center-list-data'),
    re_path(r'^data/center-list/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/'
            r'(?P<sub_constituency_id>(\d+))/$',
            center_list_view.CenterListView.as_view(),
            name='center-and-stations-in-audit-list'),
    re_path(r'^data/center-list-data/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/'
            r'(?P<sub_constituency_id>(\d+))/$',
            center_list_view.CenterListDataView.as_view(),
            name='center-list-data'),
    re_path(r'^data/races-list/(?P<tally_id>(\d+))/$',
            race_list_view.RaceListView.as_view(),
            name='races-list'),
    re_path(r'^data/candidate-list/(?P<tally_id>(\d+))/$',
            candidate_list_view.CandidateListView.as_view(),
            name='candidate-list'),
    re_path(r'^data/candidate-list-data/(?P<tally_id>(\d+))/$',
            candidate_list_view.CandidateListDataView.as_view(),
            name='candidate-list-data'),
    re_path(r'^reports/internal/candidate-list-by-votes/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/$',
            candidate_list_by_votes.CandidateVotesListView.as_view(),
            name='candidate-list-by-votes'),
    re_path(r'^reports/internal/candidates-list-by-votes-list-data/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/$',
            candidate_list_by_votes.CandidateVotesListDataView.as_view(),
            name='candidates-list-by-votes-list-data'),
    re_path(r'^reports/internal/candidate-list-by-votes/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/$',
            candidate_list_by_votes.CandidateVotesListView.as_view(),
            name='candidate-list-by-votes'),
    re_path(r'^reports/internal/candidates-list-by-votes-list-data/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/$',
            candidate_list_by_votes.CandidateVotesListDataView.as_view(),
            name='candidates-list-by-votes-list-data'),
    re_path(r'^reports/internal/candidate-list-by-votes/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/'
            r'(?P<sub_constituency_id>(\d+))/$',
            candidate_list_by_votes.CandidateVotesListView.as_view(),
            name='candidate-list-by-votes'),
    re_path(r'^reports/internal/candidates-list-by-votes-list-data/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/(?P<sub_constituency_id>(\d+))/$',
            candidate_list_by_votes.CandidateVotesListDataView.as_view(),
            name='candidates-list-by-votes-list-data'),
    re_path(r'^data/candidate-list-per-office/(?P<tally_id>(\d+))/'
            r'(?P<office_id>(\d+))/$',
            candidate_list_view.CandidateListView.as_view(),
            name='candidate-list-per-office'),
    re_path(r'^data/candidate-list-data-per-office/(?P<tally_id>(\d+))/'
            r'(?P<office_id>(\d+))/$',
            candidate_list_view.CandidateListDataView.as_view(),
            name='candidate-list-data-per-office'),
    re_path(r'^data/form-list/(?P<tally_id>(\d+))/$',
            form_list_view.FormListView.as_view(),
            name='form-list'),
    re_path(r'^data/form-list/(?P<tally_id>(\d+))/(?P<state>.*)/$',
            form_list_view.FormListView.as_view(),
            name='form-list'),
    re_path(r'^data/form-list-data/(?P<tally_id>(\d+))/$',
            form_list_view.FormListDataView.as_view(),
            name='form-list-data'),
    re_path(r'^data/form-not-received.(?P<format>(csv))/(?P<tally_id>(\d+))/$',
            form_list_view.FormNotReceivedListView.as_view(),
            name='form-not-received-view'),
    re_path(r'^data/form-not-received/(?P<tally_id>(\d+))/$',
            form_list_view.FormNotReceivedListView.as_view(),
            name='form-not-received-view'),
    re_path(r'^data/form-not-received-data/(?P<tally_id>(\d+))/$',
            form_list_view.FormNotReceivedDataView.as_view(),
            name='form-not-received-data'),
    re_path(r'^data/forms-for-race/(?P<tally_id>(\d+))/(?P<ballot>.*)/$',
            form_list_view.FormsForRaceView.as_view(),
            name='forms-for-race'),
    re_path(r'^data/forms-for-race-data/(?P<tally_id>(\d+))/(?P<ballot>.*)/$',
            form_list_view.FormListDataView.as_view(),
            name='forms-for-race-data'),

    re_path(r'^super-administrator/tallies$',
            super_admin.TalliesView.as_view(),
            name='super-administrator-tallies'),
    re_path(r'^super-administrator/(?P<tally_id>(\d+))/$',
            super_admin.DashboardView.as_view(), name='super-administrator'),
    re_path(r'^super-administrator/create-form/(?P<tally_id>(\d+))/$',
            super_admin.CreateResultFormView.as_view(),
            name='create-form'),
    re_path(r'^super-administrator/update-form/(?P<tally_id>(\d+))/'
            r'(?P<form_id>(\d+))$',
            super_admin.EditResultFormView.as_view(),
            name='update-form'),
    re_path(r'^super-administrator/delete-form/(?P<tally_id>(\d+))/'
            r'(?P<form_id>(\d+))$',
            super_admin.RemoveResultFormConfirmationView.as_view(),
            name='remove-form-confirmation'),
    re_path(r'^super-administrator/form-progress/(?P<tally_id>(\d+))/$',
            super_admin.FormProgressView.as_view(),
            name='form-progress'),
    re_path(r'^super-administrator/form-duplicates/(?P<tally_id>(\d+))/$',
            super_admin.FormDuplicatesView.as_view(),
            name='form-duplicates'),
    re_path(r'^super-administrator/form-clearance/(?P<tally_id>(\d+))/$',
            super_admin.FormClearanceView.as_view(),
            name='form-clearance'),
    re_path(r'^super-administrator/form-audit/(?P<tally_id>(\d+))/$',
            super_admin.FormAuditView.as_view(),
            name='form-audit'),
    re_path(
        r'^super-administrator/form-results-duplicates/(?P<tally_id>(\d+))/$',
        super_admin.FormResultsDuplicatesView.as_view(),
        name='form-results-duplicates'),
    re_path(r'^super-administrator/form-action-list/(?P<tally_id>(\d+))/$',
            super_admin.FormActionView.as_view(),
            name='form-action-view'),
    re_path(r'^super-administrator/duplicate-result-tracking/'
            r'(?P<tally_id>(\d+))/$',
            super_admin.DuplicateResultTrackingView.as_view(),
            name='duplicate-result-tracking'),
    re_path(r'^super-administrator/duplicate_result_form/(?P<tally_id>(\d+))/'
            r'(?P<barcode>(\d+))/(?P<ballot_id>(\d+))/$',
            super_admin.DuplicateResultFormView.as_view(),
            name='duplicate_result_form'),
    re_path(r'^super-administrator/form-progress-data/(?P<tally_id>(\d+))/$',
            super_admin.FormProgressDataView.as_view(),
            name='form-progress-data'),
    re_path(r'^super-administrator/form-duplicates-data/(?P<tally_id>(\d+))/$',
            super_admin.FormDuplicatesDataView.as_view(),
            name='form-duplicates-data'),
    re_path(r'^super-administrator/form-clearance-data/(?P<tally_id>(\d+))/$',
            super_admin.FormClearanceDataView.as_view(),
            name='form-clearance-data'),
    re_path(r'^super-administrator/form-audit-data/(?P<tally_id>(\d+))/$',
            super_admin.FormAuditDataView.as_view(),
            name='form-audit-data'),
    re_path(r'^super-administrator/results-(?P<report>.*).csv/'
            r'(?P<tally_id>(\d+))/$',
            super_admin.ResultExportView.as_view(),
            name='result-export'),
    re_path(r'^super-administrator/results/(?P<tally_id>(\d+))/$',
            super_admin.ResultExportView.as_view(),
            name='result-export'),
    re_path(r'^super-administrator/remove-center/(?P<tally_id>(\d+))/$',
            super_admin.RemoveCenterView.as_view(),
            name='remove-center'),
    re_path(r'^super-administrator/remove-center/(?P<tally_id>(\d+))/'
            r'(?P<center_code>(\d+))$',
            super_admin.RemoveCenterConfirmationView.as_view(),
            name='remove-center-confirmation'),
    re_path(r'^super-administrator/edit-center/(?P<tally_id>(\d+))/'
            r'(?P<center_code>(\d+))$',
            super_admin.EditCenterView.as_view(),
            name='edit-center'),
    re_path(r'^super-administrator/create-center/(?P<tally_id>(\d+))/$',
            super_admin.CreateCenterView.as_view(),
            name='create-center'),
    re_path(r'^super-administrator/disable/(?P<tally_id>(\d+))/'
            r'(?P<center_code>(\d+))/(?P<station_number>(\d+))?$',
            super_admin.DisableEntityView.as_view(),
            name='disable'),
    re_path(r'^super-administrator/enable/(?P<tally_id>(\d+))/'
            r'(?P<center_code>(\d+))/(?P<station_number>(\d+))?$',
            super_admin.EnableEntityView.as_view(),
            name='enable'),
    re_path(r'^super-administrator/create-race/(?P<tally_id>(\d+))/$',
            super_admin.CreateRaceView.as_view(),
            name='create-race'),
    re_path(r'^super-administrator/edit-race/(?P<tally_id>(\d+))/'
            r'(?P<id>(\d+))$',
            super_admin.EditRaceView.as_view(),
            name='edit-race'),
    re_path(r'^super-administrator/disable-race/(?P<tally_id>(\d+))/'
            r'(?P<race_id>(\d+))$',
            super_admin.DisableRaceView.as_view(),
            name='disable-race'),
    re_path(r'^super-administrator/enable-race/(?P<tally_id>(\d+))/'
            r'(?P<race_id>(\d+))$',
            super_admin.EnableRaceView.as_view(),
            name='enable-race'),
    re_path(r'^super-administrator/candidate-disable/(?P<tally_id>(\d+))/'
            r'(?P<candidateId>(\d+))$',
            super_admin.DisableCandidateView.as_view(),
            name='candidate-disable'),
    re_path(r'^super-administrator/candidate-enable/(?P<tally_id>(\d+))/'
            r'(?P<candidateId>(\d+))$',
            super_admin.EnableCandidateView.as_view(),
            name='candidate-enable'),
    re_path(r'^super-administrator/create-station/(?P<tally_id>(\d+))/$',
            super_admin.CreateStationView.as_view(),
            name='create-station'),
    re_path(r'^super-administrator/remove-station/(?P<tally_id>(\d+))/$',
            super_admin.RemoveStationView.as_view(),
            name='remove-station'),
    re_path(r'^super-administrator/quarantine-checks$',
            super_admin.QuarantineChecksListView.as_view(),
            name='quarantine-checks'),
    re_path(r'^super-administrator/quarantine-checks/config/'
            r'(?P<checkId>(\d+))$',
            super_admin.QuarantineChecksConfigView.as_view(),
            name='quarantine-checks-config'),
    re_path(r'^super-administrator/remove-station/(?P<tally_id>(\d+))/'
            r'(?P<station_id>(\d+))$',
            super_admin.RemoveStationConfirmationView.as_view(),
            name='remove-station-confirmation'),
    re_path(r'^super-administrator/edit-station/(?P<tally_id>(\d+))/'
            r'(?P<station_id>(\d+))$',
            super_admin.EditStationView.as_view(),
            name='edit-station'),
    re_path(r'^super-admin/user-list/(?P<tally_id>(\d+))/$',
            user_list_view.UserTallyListView.as_view(),
            name='user-tally-list'),
    re_path(r'^super-admin/user-list-data/(?P<tally_id>(\d+))/$',
            user_list_view.UserTallyListDataView.as_view(),
            name='user-tally-list-data'),
    re_path(r'^super-admin/edit-user/(?P<tally_id>(\d+))/(?P<user_id>(\d+))/$',
            super_admin.EditUserView.as_view(),
            name='edit-user-tally'),
    re_path(r'^super-admin/create-user/(?P<tally_id>(\d+))/$',
            super_admin.CreateUserView.as_view(),
            name='create-user-tally'),

    re_path(r'^data-entry/(?P<tally_id>(\d+))/$',
            data_entry.DataEntryView.as_view(),
            name='data-entry'),
    re_path(r'^data-entry/enter-center-details/(?P<tally_id>(\d+))/$',
            data_entry.CenterDetailsView.as_view(),
            name='data-entry-enter-center-details'),
    re_path(r'^data-entry/enter-results/(?P<tally_id>(\d+))/$',
            data_entry.EnterResultsView.as_view(),
            name='enter-results'),
    re_path(r'^data-entry/success/(?P<tally_id>(\d+))/$',
            data_entry.ConfirmationView.as_view(),
            name='data-entry-success'),

    re_path(r'^intake/center-details/(?P<tally_id>(\d+))/$',
            intake.CenterDetailsView.as_view(),
            name='intake'),
    re_path(r'^intake/enter-center/(?P<tally_id>(\d+))/$',
            intake.EnterCenterView.as_view(),
            name='intake-enter-center'),
    re_path(r'^intake/check-center-details/(?P<tally_id>(\d+))/$',
            intake.CheckCenterDetailsView.as_view(),
            name='check-center-details'),
    re_path(r'^intake/printcover/(?P<tally_id>(\d+))/$',
            intake.PrintCoverView.as_view(),
            name='intake-printcover'),
    re_path(r'^intake/clearance/(?P<tally_id>(\d+))/$',
            intake.ClearanceView.as_view(),
            name='intake-clearance'),
    re_path(r'^intake/intaken/(?P<tally_id>(\d+))/$',
            intake.ConfirmationView.as_view(),
            name='intaken'),
    re_path(r'^intake/intake-printed/(?P<resultFormPk>(\d+))$',
            intake.IntakePrintedView.as_view(),
            name='intake-printed'),

    re_path(r'^quality-control/home/(?P<tally_id>(\d+))/$',
            quality_control.QualityControlView.as_view(),
            name='quality-control'),
    re_path(r'^quality-control/dashboard/(?P<tally_id>(\d+))/$',
            quality_control.QualityControlDashboardView.as_view(),
            name='quality-control-dashboard'),
    re_path(r'^quality-control/confirm-reject/(?P<tally_id>(\d+))/$',
            quality_control.ConfirmFormResetView.as_view(),
            name='quality-control-confirm-reject'),
    re_path(r'^quality-control/reject/(?P<tally_id>(\d+))/$',
            TemplateView.as_view(template_name='quality_control/reject.html'),
            name='quality-control-reject'),
    re_path(r'^quality-control/print/(?P<tally_id>(\d+))/$',
            quality_control.PrintView.as_view(),
            name='quality-control-print'),
    re_path(r'^quality-control/success/(?P<tally_id>(\d+))/$',
            quality_control.ConfirmationView.as_view(),
            name='quality-control-success'),

    re_path(r'^corrections/(?P<tally_id>(\d+))/$',
            corrections.CorrectionView.as_view(),
            name='corrections'),
    re_path(r'^corrections/match/(?P<tally_id>(\d+))/$',
            corrections.CorrectionMatchView.as_view(),
            name='corrections-match'),
    re_path(r'^corrections/required/(?P<tally_id>(\d+))/$',
            corrections.CorrectionRequiredView.as_view(),
            name='corrections-required'),
    re_path(r'^corrections/success/(?P<tally_id>(\d+))/$',
            corrections.ConfirmationView.as_view(),
            name='corrections-success'),

    re_path(r'^audit/(?P<tally_id>(\d+))/$',
            audit.DashboardView.as_view(),
            name='audit'),
    re_path(r'^audit/(?P<tally_id>(\d+))/(?P<format>(csv))/$',
            audit.DashboardView.as_view(),
            name='audit-csv'),
    re_path(r'^audit/new/(?P<tally_id>(\d+))/$',
            audit.CreateAuditView.as_view(),
            name='audit-new'),
    re_path(r'^audit/print/(?P<tally_id>(\d+))/$',
            audit.PrintCoverView.as_view(),
            name='audit-print'),
    re_path(r'^audit/review/(?P<tally_id>(\d+))/$',
            audit.ReviewView.as_view(),
            name='audit-review'),

    re_path(r'^clearance/(?P<tally_id>(\d+))/$',
            clearance.DashboardView.as_view(),
            name='clearance'),
    re_path(r'^clearance/(?P<tally_id>(\d+))/(?P<format>(csv))/$',
            clearance.DashboardView.as_view(),
            name='clearance-csv'),
    re_path(r'^clearance/new/(?P<tally_id>(\d+))/$',
            super_admin.CreateResultFormView.as_view(
                clearance_result_form=True),
            name='clearance-new'),
    re_path(r'^clearance/print/(?P<tally_id>(\d+))/$',
            clearance.PrintCoverView.as_view(),
            name='clearance-print'),
    re_path(r'^clearance/review/(?P<tally_id>(\d+))/$',
            clearance.ReviewView.as_view(),
            name='clearance-review'),
    re_path(r'^clearance/create/(?P<tally_id>(\d+))/$',
            clearance.CreateClearanceView.as_view(),
            name='clearance-create'),
    re_path(r'^clearance/check-center-details/(?P<tally_id>(\d+))/$',
            clearance.CheckCenterDetailsView.as_view(),
            name='clearance-check-center-details'),
    re_path(r'^clearance/add/(?P<tally_id>(\d+))/$',
            clearance.AddClearanceFormView.as_view(),
            name='clearance-add'),
    re_path(r'^clearance/clearance-printed/(?P<resultFormPk>(\d+))$',
            clearance.ClearancePrintedView.as_view(),
            name='clearance-printed'),

    re_path(r'^reports/internal/regions/(?P<tally_id>(\d+))/$',
            administrative_areas_reports.RegionsReportsView.as_view(),
            name='reports-regions'),
    re_path(r'^reports/internal/regions/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/'
            r'(?P<report_type>(centers-and-stations-in-audit-report))/$',
            administrative_areas_reports.RegionsReportsView.as_view(),
            name='regions-discrepancy-report'),
    re_path(r'^reports/internal/regions/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/'
            r'(?P<report_type>(votes-per-candidate-report))/$',
            administrative_areas_reports.RegionsReportsView.as_view(),
            name='region-votes-per-candidate'),

    re_path(r'^reports/internal/regions/(?P<tally_id>(\d+))/'
            r'(?P<export_type>(turnout-csv))/$',
            administrative_areas_reports.RegionsReportsView.as_view(),
            name='regions-turnout-csv'),
    re_path(r'^reports/internal/regions/(?P<tally_id>(\d+))/'
            r'(?P<export_type>(summary-csv))/$',
            administrative_areas_reports.RegionsReportsView.as_view(),
            name='regions-summary-csv'),

    re_path(r'^reports/internal/constituencies/turnout/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(
                template_name="reports/turnout_report.html"
            ),
            name='constituency-turnout-report'),
    re_path(r'^reports/internal/constituencies/summary/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(
                template_name="reports/summary_report.html"
            ),
            name='constituency-summary-report'),
    re_path(r'^reports/internal/constituencies/discrepancy/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(
                template_name="reports/process_discrepancy_report.html"
            ),
            name='constituency-discrepancy-report'),
    re_path(r'^reports/internal/constituencies/centers-and-stations-in-audit/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/'
            r'(?P<report_type>(centers-and-stations-in-audit-report))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(),
            name='constituency-discrepancy-report'),
    re_path(r'^reports/internal/constituencies/progressive/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(
                template_name="reports/progressive_report.html"
            ),
            name='constituency-progressive-report'),
    re_path(r'^reports/internal/constituencies/votes-per-candidate/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/'
            r'(?P<report_type>(votes-per-candidate-report))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(),
            name='constituency-votes-per-candidate'),

    re_path(r'^reports/internal/constituencies/discrepancy/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<export_type>(discrepancy-csv))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(),
            name='constituencies-discrepancy-csv'),
    re_path(r'^reports/internal/constituencies/progressive/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<export_type>(progressive-csv))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(),
            name='constituencies-progressive-csv'),
    re_path(r'^reports/internal/constituencies/turnout/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<export_type>(turnout-csv))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(),
            name='constituencies-turnout-csv'),
    re_path(r'^reports/internal/constituencies/summary/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<export_type>(summary-csv))/$',
            administrative_areas_reports.ConstituencyReportsView.as_view(),
            name='constituencies-summary-csv'),

    re_path(r'^reports/internal/sub-constituencies/turnout/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(
                template_name="reports/turnout_report.html"
            ),
            name='sub-constituency-turnout-report'),
    re_path(r'^reports/internal/sub-constituencies/summary/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(
                template_name="reports/summary_report.html"
            ),
            name='sub-constituency-summary-report'),
    re_path(r'^reports/internal/sub-constituencies/discrepancy/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(
                template_name="reports/process_discrepancy_report.html"
            ),
            name='sub-constituency-discrepancy-report'),
    re_path(r'^reports/internal/sub-constituencies/'
            r'centers-and-stations-in-audit/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/'
            r'(?P<sub_constituency_id>(\d+))/'
            r'(?P<report_type>(centers-and-stations-in-audit-report))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(),
            name='sub-constituency-discrepancy-report'),
    re_path(r'^reports/internal/sub-constituencies/progressive/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(
                template_name="reports/progressive_report.html"
            ),
            name='sub-constituency-progressive-report'),
    re_path(r'^reports/internal/sub-constituencies/'
            r'votes-per-candidate/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/'
            r'(?P<sub_constituency_id>(\d+))/'
            r'(?P<report_type>(votes-per-candidate-report))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(),
            name='sub-constituency-votes-per-candidate'),
    re_path(r'^reports/internal/sub-constituencies/'
            r'votes-per-candidate/(?P<tally_id>(\d+))/'
            r'(?P<region_id>(\d+))/(?P<constituency_id>(\d+))/'
            r'(?P<sub_constituency_id>(\d+))/'
            r'(?P<report_type>(candidate-list-sorted-by-ballots-number))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(),
            name='sub-constituency-votes-per-candidate'),

    re_path(r'^reports/internal/sub-constituencies/discrepancy/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/(?P<export_type>(discrepancy-csv))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(),
            name='sub-constituencies-discrepancy-csv'),
    re_path(r'^reports/internal/sub-constituencies/progressive/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/(?P<export_type>(progressive-csv))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(),
            name='sub-constituencies-progressive-csv'),
    re_path(r'^reports/internal/sub-constituencies/turnout/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/(?P<export_type>(turnout-csv))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(),
            name='sub-constituencies-turnout-csv'),
    re_path(r'^reports/internal/sub-constituencies/summary/'
            r'(?P<tally_id>(\d+))/(?P<region_id>(\d+))/'
            r'(?P<constituency_id>(\d+))/(?P<export_type>(summary-csv))/$',
            administrative_areas_reports.SubConstituencyReportsView.as_view(),
            name='sub-constituencies-summary-csv'),

    re_path(r'^reports/internal/offices/(?P<tally_id>(\d+))/$',
            offices.OfficesReportView.as_view(),
            name='reports-offices'),
    re_path(r'^reports/internal/offices/(?P<tally_id>(\d+))/(?P<option>.*)/$',
            offices.OfficesReportDownloadView.as_view(),
            name='reports-offices-export'),
    re_path(r'^reports/internal/race/(?P<tally_id>(\d+))/$',
            races.RacesReportView.as_view(),
            name='reports-races'),
    re_path(r'^reports/internal/staion-progress-list/(?P<tally_id>(\d+))/$',
            station_progress_report.StationProgressListView.as_view(),
            name='staion-progress-list'),
    re_path(r'^reports/internal/staion-progress-list-data/(?P<tally_id>(\d+))'
            r'/$',
            station_progress_report.StationProgressListDataView.as_view(),
            name='staion-progress-list-data'),
    re_path(r'^reports/internal/station-votes-per-candidate/'
            r'(?P<tally_id>(\d+))/(?P<station_number>(\d+))/$',
            votes_per_candidate.VotesPerCandidateListView.as_view(),
            name='votes-per-candidate'),
    re_path(r'^reports/internal/station-votes-per-candidate-list-data/'
            r'(?P<tally_id>(\d+))/(?P<station_number>(\d+))/$',
            votes_per_candidate.VotesPerCandidateListDataView.as_view(),
            name='votes-per-candidate-list-data'),
    re_path(r'^reports/internal/center-votes-per-candidate/'
            r'(?P<tally_id>(\d+))/(?P<center_code>(\d+))/$',
            votes_per_candidate.VotesPerCandidateListView.as_view(),
            name='votes-per-candidate'),
    re_path(r'^reports/internal/center-votes-per-candidate-list-data/'
            r'(?P<tally_id>(\d+))/(?P<center_code>(\d+))/$',
            votes_per_candidate.VotesPerCandidateListDataView.as_view(),
            name='votes-per-candidate-list-data'),

    re_path(r'^reports/internal/staff-performance-metrics/(?P<tally_id>(\d+))/'
            r'(?P<group_name>.*)/$',
            staff_performance_metrics.StaffPerformanceMetricsView.as_view(),
            name='staff-perfomance-metrics'),

    re_path(r'^reports/internal/supervisors-approvals/(?P<tally_id>(\d+))/$',
            staff_performance_metrics.SupervisorsApprovalsView.as_view(),
            name='supervisors-approvals'),

    re_path(r'^reports/internal/track-corrections/(?P<tally_id>(\d+))/$',
            staff_performance_metrics.TrackCorrections.as_view(),
            name='track-corrections'),

    re_path(r'^reports/internal/station-overall-votes/(?P<tally_id>(\d+))/$',
            overall_votes.OverallVotes.as_view(),
            name='station-overall-votes'),

    re_path(r'^reports/internal/center-overall-votes/(?P<tally_id>(\d+))/$',
            overall_votes.OverallVotes.as_view(),
            name='center-overall-votes'),

    re_path(r'^tally-manager$',
            tally_manager.DashboardView.as_view(), name='tally-manager'),
    re_path(r'^tally-manager/global-settings/(?P<site_id>(\d+))/$',
            tally_manager.SetUserTimeOutView.as_view(),
            name='global-settings'),
    re_path(r'^tally-manager/user-list/(?P<role>(user|admin))$',
            user_list_view.UserListView.as_view(),
            name='user-list'),
    re_path(r'^tally-manager/user-list-data/(?P<role>(user|admin))$',
            user_list_view.UserListDataView.as_view(),
            name='user-list-data'),
    re_path(r'^tally-manager/edit-user/(?P<userId>(\d+))$',
            tally_manager.EditUserView.as_view(),
            name='edit-user'),
    re_path(r'^tally-manager/create-user/(?P<role>(user|admin))$',
            tally_manager.CreateUserView.as_view(),
            name='create-user'),
    re_path(r'^tally-manager/remove-user/(?P<userId>.+)$',
            tally_manager.RemoveUserConfirmationView.as_view(),
            name='remove-user-confirmation'),
    re_path(r'^tally-manager/create-tally$',
            tally_manager.CreateTallyView.as_view(), name='create-tally'),
    re_path(r'^tally-manager/update-tally/(?P<tally_id>(\d+))/$',
            tally_manager.TallyUpdateView.as_view(), name='update-tally'),
    re_path(r'^tally-manager/tally-files/(?P<tally_id>(\d+))/$',
            tally_manager.TallyFilesFormView.as_view(),
            name='tally-files-form'),
    re_path(r'^tally-manager/remove-tally/(?P<tally_id>(\d+))/$',
            tally_manager.TallyRemoveView.as_view(), name='remove-tally'),
    re_path(r'^tally-manager/create-tally/batch-view/(?P<tally_id>.*)/'
            r'(?P<subconst_file>.*)/(?P<subconst_file_lines>(\d+))/'
            r'(?P<centers_file>.*)/(?P<centers_file_lines>(\d+))/'
            r'(?P<stations_file>.*)/(?P<stations_file_lines>(\d+))/'
            r'(?P<candidates_file>.*)/(?P<candidates_file_lines>(\d+))/'
            r'(?P<ballots_order_file>.*)/(?P<ballots_order_file_lines>(\d+))/'
            r'(?P<result_forms_file>.*)/(?P<result_forms_file_lines>(\d+))/$',
            tally_manager.BatchView.as_view(), name='batch-view'),
    re_path(r'^tally-manager/data/tally-list$',
            tally_list_view.TallyListView.as_view(),
            name='tally-list'),
    re_path(r'^tally-manager/data/tally-list-data$',
            tally_list_view.TallyListDataView.as_view(),
            name='tally-list-data'),

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
