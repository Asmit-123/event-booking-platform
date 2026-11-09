from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailAuthenticationForm
from .throttle import throttle_logins

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        throttle_logins(
            auth_views.LoginView.as_view(
                template_name="accounts/login.html",
                authentication_form=EmailAuthenticationForm,
                redirect_authenticated_user=True,
            )
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]