from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth import views as auth_views

from libya_tally.apps.tally import views as tally_views

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
    url(r'^$', tally_views.HomeView.as_view(), name='home'),
    url(r'^intake$', tally_views.IntakeClerkView.as_view(),
        name='intake-clerk'),
    url(r'^intake/center-details$', tally_views.CenterDetailView.as_view(),
        name='center-details'),
    url(r'^intake/check-center-details$',
        tally_views.CheckCenterDetailView.as_view(),
        name='check-center-details'),
    url(r'^intake/printcover$',
        tally_views.IntakePrintCoverView.as_view(),
        name='intake-printcover'),
    url(r'^intake/clearance$',
        tally_views.IntakeClearanceView.as_view(),
        name='intake-clearance'),

    url(r'^accounts/', include(accounts_urls)),
    url(r'^admin/', include(admin.site.urls)),
)
