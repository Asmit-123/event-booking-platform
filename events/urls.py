from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.home, name="home"),
    path("organizer/", views.organizer_dashboard, name="organizer_dashboard"),
    path("organizer/events/new/", views.event_create, name="event_create"),
    path("organizer/events/<int:pk>/edit/", views.event_edit, name="event_edit"),
]