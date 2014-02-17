from django.contrib.auth import views as auth_views
from django.shortcuts import redirect


def login(request, *args, **kwargs):
    response = auth_views.login(request, *args, **kwargs)
    if response.status_code == 302:
        try:
            if request.user.userprofile.reset_password:
                return redirect('password_change')
        except AttributeError:
            pass
    return response
