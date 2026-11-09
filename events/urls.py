from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.home, name="home"),
    path("organizer/", views.organizer_dashboard, name="organizer_dashboard"),
    path("organizer/events/new/", views.event_create, name="event_create"),
    path("organizer/events/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("organizer/events/<int:pk>/cancel/", views.event_cancel, name="event_cancel"),
    path("organizer/events/<int:pk>/attendees/", views.event_attendees, name="event_attendees"),
    path("events/", views.event_list, name="event_list"),
    path("events/<int:pk>/", views.event_detail, name="event_detail"),
    path("organizer/events/<int:pk>/attendees/export.csv", views.event_attendees_csv, name="event_attendees_csv"),
    path("events/<int:pk>/calendar.ics", views.event_calendar, name="event_calendar"),
]