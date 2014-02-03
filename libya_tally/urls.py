from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from libya_tally.apps.tally.views import data_entry_clerk, home, intake_clerk

admin.autodiscover()

accounts_urls = patterns(
    '',
    url(r'^login/$', auth_views.login,
        {'template_name': 'registration/login.html'},
        name='login'),
    url(r'^logout/$', auth_views.logout, {'next_page': '/'}, name='logout'),
)

urlpatterns = patterns(
    '',
    url(r'^$', home.HomeView.as_view(), name='home'),
    url(r'^data-entry$', data_entry_clerk.CenterDetailsView.as_view(),
        name='data-entry-clerk'),
    url(r'^data-entry/check-center-details$',
        data_entry_clerk.CheckCenterDetailsView.as_view(),
        name='data-entry-check-center-details'),
    url(r'^data-entry/enter-results',
        data_entry_clerk.EnterResultsView.as_view(),
        name='enter-results'),
    url(r'^intake$', intake_clerk.IntakeClerkView.as_view(),
        name='intake-clerk'),
    url(r'^intake/center-details$', intake_clerk.CenterDetailsView.as_view(),
        name='center-details'),
    url(r'^intake/check-center-details$',
        intake_clerk.CheckCenterDetailsView.as_view(),
        name='check-center-details'),
    url(r'^intake/printcover$',
        intake_clerk.IntakePrintCoverView.as_view(),
        name='intake-printcover'),
    url(r'^intake/clearance$',
        intake_clerk.IntakeClearanceView.as_view(),
        name='intake-clearance'),
    url(r'^intake/intaken',
        TemplateView.as_view(template_name='tally/intake_success.html'),
        name='intaken'),

    url(r'^accounts/', include(accounts_urls)),
    url(r'^admin/', include(admin.site.urls)),
)
