from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth import views as auth_views

from libya_tally.apps.tally.views.home import HomeView

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
    url(r'^$', HomeView.as_view(), name='home'),

    url(r'^accounts/', include(accounts_urls)),
    url(r'^admin/', include(admin.site.urls)),
)
