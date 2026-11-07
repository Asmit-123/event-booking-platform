from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer", "start_datetime", "seat_limit", "status")
    list_filter = ("status",)
    search_fields = ("title", "venue", "organizer__email")
    list_select_related = ("organizer",)