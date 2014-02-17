from django.contrib.auth import views as auth_views

from django.shortcuts import redirect
from libya_tally.apps.tally.models.user_profile import UserProfile


def login(request, *args, **kwargs):
    response = auth_views.login(request, *args, **kwargs)
    if response.status_code == 302:
        try:
            if request.user.userprofile.reset_password:
                return redirect('password_change')
        except AttributeError:
            pass
        except UserProfile.DoesNotExist:
            profile = UserProfile(user_ptr=request.user)
            profile.save_base(raw=True)
            return redirect('password_change')
    return response
