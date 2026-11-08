from django.urls import path

from . import views

app_name = "registrations"

urlpatterns = [
    path("my-registrations/", views.my_registrations, name="my_registrations"),
]