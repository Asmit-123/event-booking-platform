from django.contrib import admin
from django.urls import include, path

from accounts.throttle import throttle_logins

# The admin login gets the same brute-force protection as the site login.
admin.site.login = throttle_logins(admin.site.login)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("registrations.urls")),
    path("", include("events.urls")),
]