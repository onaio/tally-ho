from django.contrib import admin  # flake8: noqa

from libya_tally.apps.tally.models.user_profile import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    pass

admin.site.register(UserProfile, UserProfileAdmin)
