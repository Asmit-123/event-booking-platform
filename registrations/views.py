from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import attendee_required
from events.models import Event

from . import services


@attendee_required
def my_registrations(request):
    return render(request, "registrations/my_registrations.html")


@attendee_required
@require_POST
def register(request, pk):
    event = get_object_or_404(Event, pk=pk)

    try:
        services.register_for_event(request.user, event.pk)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, f"You are registered for \u201c{event.title}\u201d.")

    return redirect("events:event_detail", pk=event.pk)