from django.contrib import admin

from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "attendee", "created_at")
    list_select_related = ("event", "attendee")
    search_fields = ("event__title", "attendee__email")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False